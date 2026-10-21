"use client";

import Link from "next/link";
import Image from "next/image";
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
          <Image className={styles.brandMark} src="/brand/logo/nova-mark-image2.5-v1.png" alt="" width={50} height={50} priority /><strong>NOVA<small>企业商城</small></strong>
        </Link>
        {isRegister && <span className={styles.welcomeRegister}>欢迎注册</span>}
        <p>{isRegister ? "已有账号？" : "还没有账号？"}<Link href={isRegister ? "/login" : "/register"}>{isRegister ? "立即登录" : "免费注册"}</Link></p>
      </header>
      {!isRegister ? (
        <section className={styles.loginStage}>
          <div className={styles.loginStageInner}>
            <div className={styles.loginPromo}>
              <div className={styles.loginPromoIcon}><CommerceIcon name="account" size={132} largeSource priority /></div>
              <span>NOVA MEMBER</span>
              <h1>企业采购，登录更省心</h1>
              <p>品牌直供 · 企业专价 · 智能客服 · 履约保障</p>
            </div>
            <div className={styles.loginCard}>
              <div className={styles.loginTabs}><span>扫码登录</span><strong>账户登录</strong></div>
              <div className={styles.loginNotice}>登录即享企业采购专属服务</div>
              <form onSubmit={submit} className={styles.loginForm}>
                <label className={styles.loginInput}><span>邮</span><input name="email" type="email" maxLength={254} autoComplete="email" aria-label="邮箱" placeholder="邮箱账号" required /></label>
                <label className={styles.loginInput}><span>密</span><input name="password" type="password" minLength={8} maxLength={72} autoComplete="current-password" aria-label="密码" placeholder="密码" required /></label>
                <div className={styles.loginMeta}><span>公共设备请勿自动保存密码</span><a href="mailto:support@nova.example">忘记密码</a></div>
                {error && <div className={styles.error} role="alert">{error}</div>}
                <button className={styles.loginButton} type="submit" disabled={loading}>{loading ? "登录中…" : "登 录"}</button>
              </form>
              <div className={styles.loginCardFooter}><span>安全登录 · 信息加密保护</span><Link href="/register">免费注册 →</Link></div>
            </div>
          </div>
        </section>
      ) : <section className={styles.registerStage}>
        <div className={styles.registerGlass}>
          <div className={styles.registerTypeTabs}><strong>个人用户注册</strong><Link href="/merchant/apply">企业用户入驻</Link></div>
          <ol className={styles.registerSteps} aria-label="注册进度">
            <li className={styles.stepActive}><b>1</b><span>填写账号信息</span></li>
            <li><b>2</b><span>确认服务协议</span></li>
            <li><b>3</b><span>注册成功</span></li>
          </ol>
          <form onSubmit={submit} className={styles.registerForm}>
            <label><span>昵称</span><input name="displayName" type="text" minLength={2} maxLength={80} autoComplete="name" placeholder="请输入您的称呼" required /></label>
            <label><span>邮箱</span><input name="email" type="email" maxLength={254} autoComplete="email" placeholder="建议使用常用邮箱" required /></label>
            <label><span>设置密码</span><input name="password" type="password" minLength={8} maxLength={72} autoComplete="new-password" placeholder="至少 8 位字符" required /></label>
            <label><span>确认密码</span><input name="confirmPassword" type="password" minLength={8} maxLength={72} autoComplete="new-password" placeholder="请再次输入密码" required /></label>
            {error && <div className={styles.registerError} role="alert">{error}</div>}
            <button className={styles.registerButton} type="submit" disabled={loading}>{loading ? "注册中…" : "同意协议并注册"}</button>
            <label className={styles.registerAgreement}><input type="checkbox" required /><span>我已阅读并同意《NOVA 用户服务协议》和《隐私政策》</span></label>
          </form>
        </div>
      </section>}
      <footer className={styles.footer}>© 2026 NOVA 企业商城 · 让企业采购更简单</footer>
    </main>
  );
}
