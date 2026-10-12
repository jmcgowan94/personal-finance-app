import { useEffect, useState } from "react";

import { useMe, useUpdateMe } from "../../api/hooks";

export function AccountInformation() {
  const { data: me, isError, error } = useMe();
  const update = useUpdateMe();
  const [firstName, setFirstName] = useState("");
  const [lastName, setLastName] = useState("");

  useEffect(() => {
    if (me) {
      setFirstName(me.first_name ?? "");
      setLastName(me.last_name ?? "");
    }
  }, [me]);

  const changed = me !== undefined && (firstName !== (me.first_name ?? "") || lastName !== (me.last_name ?? ""));

  return (
    <section className="card">
      <h2 style={{ marginBottom: 16 }}>Account Information</h2>
      {isError && <p className="error">Could not load your account: {error.message}</p>}
      <form
        className="form-row"
        onSubmit={(e) => {
          e.preventDefault();
          update.mutate({ first_name: firstName.trim(), last_name: lastName.trim() });
        }}
      >
        <div className="field">
          <label htmlFor="first-name">First name</label>
          <input
            id="first-name"
            type="text"
            autoComplete="given-name"
            maxLength={100}
            value={firstName}
            onChange={(e) => setFirstName(e.target.value)}
          />
        </div>
        <div className="field">
          <label htmlFor="last-name">Last name</label>
          <input
            id="last-name"
            type="text"
            autoComplete="family-name"
            maxLength={100}
            value={lastName}
            onChange={(e) => setLastName(e.target.value)}
          />
        </div>
        <button type="submit" className="primary" disabled={!changed || update.isPending}>
          Save
        </button>
        {update.isSuccess && !changed && <span className="success">Saved</span>}
        {update.isError && <span className="error">{update.error.message}</span>}
      </form>
    </section>
  );
}
