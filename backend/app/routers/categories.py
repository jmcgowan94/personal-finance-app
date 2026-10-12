from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.auth import get_current_user
from app.db import get_db
from app.models import Category, CategoryRule, Transaction, User
from app.schemas import (
    ApplyRulesOut,
    CategoryIn,
    CategoryOut,
    CategoryPatch,
    RuleIn,
    RuleOut,
    RulePatch,
)
from app.services.categorize import apply_rules, validate_pattern
from app.services.ownership import get_owned

router = APIRouter(tags=["categories"])


def _ensure_unique_name(db: Session, user_id: int, name: str, exclude_id: int | None = None) -> None:
    stmt = select(Category).where(Category.user_id == user_id, Category.name == name)
    if exclude_id:
        stmt = stmt.where(Category.id != exclude_id)
    if db.scalar(stmt):
        raise HTTPException(status.HTTP_409_CONFLICT, "A category with that name already exists")


@router.get("/categories", response_model=list[CategoryOut])
def list_categories(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    return db.scalars(select(Category).where(Category.user_id == user.id).order_by(Category.name)).all()


@router.post("/categories", response_model=CategoryOut, status_code=status.HTTP_201_CREATED)
def create_category(body: CategoryIn, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    _ensure_unique_name(db, user.id, body.name)
    category = Category(user_id=user.id, **body.model_dump())
    db.add(category)
    db.commit()
    return category


@router.patch("/categories/{category_id}", response_model=CategoryOut)
def update_category(
    category_id: int,
    body: CategoryPatch,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    category = get_owned(db, Category, category_id, user.id)
    changes = body.model_dump(exclude_unset=True)
    if "name" in changes:
        _ensure_unique_name(db, user.id, changes["name"], exclude_id=category.id)
    for key, value in changes.items():
        setattr(category, key, value)
    db.commit()
    return category


@router.delete("/categories/{category_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_category(category_id: int, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """Delete a category and its rules. Its transactions become uncategorised."""
    category = get_owned(db, Category, category_id, user.id)
    for txn in db.scalars(
        select(Transaction).where(Transaction.user_id == user.id, Transaction.category_id == category.id)
    ):
        txn.category_id = None
        txn.category_locked = False
    db.delete(category)
    db.commit()


@router.get("/category-rules", response_model=list[RuleOut])
def list_rules(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    return db.scalars(
        select(CategoryRule).where(CategoryRule.user_id == user.id).order_by(CategoryRule.id)
    ).all()


def _validate_rule(pattern: str, match_type: str) -> None:
    try:
        validate_pattern(pattern, match_type)
    except ValueError as exc:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_CONTENT, str(exc)) from None


@router.post("/category-rules", response_model=RuleOut, status_code=status.HTTP_201_CREATED)
def create_rule(body: RuleIn, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    get_owned(db, Category, body.category_id, user.id)
    _validate_rule(body.pattern, body.match_type)
    rule = CategoryRule(user_id=user.id, **body.model_dump())
    db.add(rule)
    db.commit()
    return rule


@router.patch("/category-rules/{rule_id}", response_model=RuleOut)
def update_rule(
    rule_id: int,
    body: RulePatch,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    rule = get_owned(db, CategoryRule, rule_id, user.id)
    changes = body.model_dump(exclude_unset=True)
    if changes.get("category_id") is not None:
        get_owned(db, Category, changes["category_id"], user.id)
    _validate_rule(changes.get("pattern", rule.pattern), changes.get("match_type", rule.match_type))
    for key, value in changes.items():
        if value is not None:
            setattr(rule, key, value)
    db.commit()
    return rule


@router.delete("/category-rules/{rule_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_rule(rule_id: int, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    db.delete(get_owned(db, CategoryRule, rule_id, user.id))
    db.commit()


@router.post("/category-rules/apply", response_model=ApplyRulesOut)
def apply_category_rules(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """Re-run the rules over every transaction not categorised by hand."""
    return ApplyRulesOut(updated=apply_rules(db, user.id))
