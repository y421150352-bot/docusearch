import { useState } from "react";
import type { FormEvent } from "react";

import { login } from "../api";
import type { AuthUser } from "../types";

type LoginPageProps = {
  onLogin: (user: AuthUser) => void;
};

export function LoginPage({ onLogin }: LoginPageProps) {
  const [username, setUsername] = useState("root");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setError("");
    setLoading(true);
    try {
      const result = await login(username.trim(), password);
      onLogin(result.data.user);
    } catch {
      setError("用户名或密码错误，请重试。");
    } finally {
      setLoading(false);
    }
  }

  return (
    <main className="auth-page">
      <section className="auth-card">
        <img
          className="auth-logo"
          src="/sheep-docusearch.png"
          alt="DocuSearch 小羊图标"
        />
        <p className="auth-kicker">DOCUSEARCH</p>
        <h1>登录文献研究助手</h1>
        <p className="auth-subtitle">进入你的私有知识库工作区</p>

        <form onSubmit={handleSubmit} className="auth-form">
          <label>
            用户名
            <input
              value={username}
              onChange={(event) => setUsername(event.target.value)}
              autoComplete="username"
              required
            />
          </label>
          <label>
            密码
            <input
              type="password"
              value={password}
              onChange={(event) => setPassword(event.target.value)}
              autoComplete="current-password"
              required
            />
          </label>
          {error && <p className="auth-error">{error}</p>}
          <button type="submit" disabled={loading}>
            {loading ? "正在登录…" : "登录"}
          </button>
        </form>
      </section>
    </main>
  );
}
