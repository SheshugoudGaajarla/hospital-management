"use client";

import { FormEvent, useEffect, useState } from "react";

import { AppShell } from "@/src/components/AppShell";
import { AuthGuard } from "@/src/components/AuthGuard";
import { AppUser, createUser, listUsers } from "@/src/lib/api";
import { AppRole, getToken } from "@/src/lib/auth";

const creatableRoles: AppRole[] = ["doctor", "operations", "laboratory", "medical", "admin"];

export default function AdminUsersPage() {
  const [users, setUsers] = useState<AppUser[]>([]);
  const [username, setUsername] = useState("");
  const [fullName, setFullName] = useState("");
  const [role, setRole] = useState<AppRole>("doctor");
  const [password, setPassword] = useState("password123");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  async function loadUsers() {
    const token = getToken();
    if (!token) return;
    try {
      setUsers(await listUsers(token));
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to load users");
    }
  }

  useEffect(() => {
    void loadUsers();
  }, []);

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const token = getToken();
    if (!token) return;
    setLoading(true);
    setError("");
    try {
      await createUser(token, {
        username: username.trim(),
        full_name: fullName.trim(),
        role,
        password,
      });
      setUsername("");
      setFullName("");
      setRole("doctor");
      setPassword("password123");
      await loadUsers();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to create user");
    } finally {
      setLoading(false);
    }
  }

  return (
    <AuthGuard allowedRoles={["admin"]}>
      <AppShell>
        <section className="page-head theme-banner theme-dashboard">
          <h1>User Management</h1>
          <p>Create doctor, operations, laboratory, medical, and admin users from the admin workspace.</p>
        </section>

        <section className="split-grid">
          <article className="panel">
            <div className="panel-head">
              <h2>Create User</h2>
            </div>
            <form className="form-grid" onSubmit={handleSubmit}>
              <label>
                Username
                <input value={username} onChange={(event) => setUsername(event.target.value)} required />
              </label>
              <label>
                Full Name
                <input value={fullName} onChange={(event) => setFullName(event.target.value)} required />
              </label>
              <label>
                Role
                <select value={role} onChange={(event) => setRole(event.target.value as AppRole)}>
                  {creatableRoles.map((item) => (
                    <option key={item} value={item}>
                      {item}
                    </option>
                  ))}
                </select>
              </label>
              <label>
                Password
                <input type="password" value={password} onChange={(event) => setPassword(event.target.value)} required />
              </label>
              {error && <p className="error">{error}</p>}
              <button type="submit" disabled={loading}>
                {loading ? "Creating..." : "Create User"}
              </button>
            </form>
          </article>

          <article className="panel">
            <div className="panel-head">
              <h2>Current Users</h2>
            </div>
            <table className="table">
              <thead>
                <tr>
                  <th>Username</th>
                  <th>Full Name</th>
                  <th>Role</th>
                </tr>
              </thead>
              <tbody>
                {users.length === 0 ? (
                  <tr>
                    <td colSpan={3}>No users found.</td>
                  </tr>
                ) : (
                  users.map((user) => (
                    <tr key={user.id}>
                      <td>{user.username}</td>
                      <td>{user.full_name}</td>
                      <td>{user.role}</td>
                    </tr>
                  ))
                )}
              </tbody>
            </table>
          </article>
        </section>
      </AppShell>
    </AuthGuard>
  );
}
