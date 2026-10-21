"use client";

import Link from "next/link";
import { FormEvent, useState } from "react";
import { useRouter } from "next/navigation";
import { CommerceIcon } from "@/shared/ui/CommerceIcon";
import styles from "./auth.module.css";

type AuthMode = "login" | "register";

export function AuthPage({ mode }: { mode: AuthMode }) {
  const router = useRouter();
  const isRegister = mode === "register";
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setError("");
    const data = new FormData(event.currentTarget);
    const password = String(data.get("password") ?? "");
    if (isRegister && password !== String(data.get("confirmPassword") ?? "")) {
      setError("两次输入的密码不一致");
      return;
    }

    const payload = isRegister
      ? { displayName: data.get("displayName"), email: data.get("email"), password }
      : { email: data.get("email"), password };
    setLoading(true);
    try {
      const response = await fetch(`/api/auth/${mode}`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload),
      });
      if (!response.ok) {
        const result = (await response.json().catch(() => null)) as { message?: string } | null;
        setError(result?.message ?? "提交失败，请检查输入后重试");
        return;
      }
      router.push("/");
      router.refresh();
    } catch {
      setError("网络连接失败，请稍后重试");
    } finally {
      setLoading(false);
    }
  }

  return (
    <main className={styles.page}>
      <header className={styles.header}>
        <Link className={styles.brand} href="/" aria-label="返回 NOVA 企业商城首页">
          <span>N</span><strong>NOVA<small>企业商城</small></strong>
        </Link>
        <p>{isRegister ? "已有账号？" : "还没有账号？"}<Link href={isRegister ? "/login" : "/register"}>{isRegister ? "立即登录" : "免费注册"}</Link></p>
      </header>
      <section className={styles.authShell}>
        <div className={styles.promoPanel}>
          <div className={styles.promoIcon}><CommerceIcon name="account" size={154} largeSource priority /></div>
          <span>NOVA MEMBER</span>
          <h1>{isRegister ? "加入 NOVA，开启高效采购" : "欢迎回到 NOVA"}</h1>
          <p>品牌直供 · 企业专价 · 智能客服 · 履约保障</p>
          <ul><li>企业商品一站式采购</li><li>订单与采购进度集中管理</li><li>7×24 小时 AI 客服支持</li></ul>
        </div>
        <div className={styles.formPanel}>
          <div className={styles.formHeading}><h2>{isRegister ? "注册 NOVA 账号" : "账号登录"}</h2><p>{isRegister ? "填写以下信息，立即成为商城会员" : "登录后查看订单并享受会员权益"}</p></div>
          <form onSubmit={submit} className={styles.form}>
            {isRegister && <label><span>昵称</span><input name="displayName" type="text" minLength={2} maxLength={80} autoComplete="name" placeholder="请输入您的称呼" required /></label>}
            <label><span>邮箱</span><input name="email" type="email" maxLength={254} autoComplete="email" placeholder="name@company.com" required /></label>
            <label><span>密码</span><input name="password" type="password" minLength={8} maxLength={72} autoComplete={isRegister ? "new-password" : "current-password"} placeholder="至少 8 位字符" required /></label>
            {isRegister && <label><span>确认密码</span><input name="confirmPassword" type="password" minLength={8} maxLength={72} autoComplete="new-password" placeholder="请再次输入密码" required /></label>}
            {isRegister && <label className={styles.agreement}><input type="checkbox" required /><span>我已阅读并同意《用户服务协议》和《隐私政策》</span></label>}
            {error && <div className={styles.error} role="alert">{error}</div>}
            <button className={styles.submitButton} type="submit" disabled={loading}>{loading ? "处理中…" : isRegister ? "同意协议并注册" : "登录"}</button>
          </form>
          <div className={styles.switchLine}>{isRegister ? "已有 NOVA 账号" : "首次来到 NOVA"}<Link href={isRegister ? "/login" : "/register"}>{isRegister ? "去登录" : "免费注册"} →</Link></div>
        </div>
      </section>
      <footer className={styles.footer}>© 2026 NOVA 企业商城 · 让企业采购更简单</footer>
    </main>
  );
}
