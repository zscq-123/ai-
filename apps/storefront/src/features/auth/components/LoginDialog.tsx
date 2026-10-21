"use client";

import { FormEvent, useEffect, useRef, useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { CommerceIcon } from "@/shared/ui/CommerceIcon";
import styles from "./loginDialog.module.css";

type LoginDialogProps = {
  className?: string;
  triggerLabel?: string;
};

export function LoginDialog({ className, triggerLabel = "您好，请登录" }: LoginDialogProps) {
  const router = useRouter();
  const dialogRef = useRef<HTMLDivElement>(null);
  const [open, setOpen] = useState(false);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  useEffect(() => {
    if (!open) return;
    const onKeyDown = (event: KeyboardEvent) => {
      if (event.key === "Escape") setOpen(false);
    };
    document.body.style.overflow = "hidden";
    window.addEventListener("keydown", onKeyDown);
    requestAnimationFrame(() => dialogRef.current?.querySelector<HTMLInputElement>("input")?.focus());
    return () => {
      document.body.style.overflow = "";
      window.removeEventListener("keydown", onKeyDown);
    };
  }, [open]);

  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setError("");
    const data = new FormData(event.currentTarget);
    setLoading(true);
    try {
      const response = await fetch("/api/auth/login", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ email: data.get("email"), password: data.get("password") }),
      });
      if (!response.ok) {
        const result = (await response.json().catch(() => null)) as { message?: string } | null;
        setError(result?.message ?? "登录失败，请检查账号和密码");
        return;
      }
      setOpen(false);
      router.refresh();
    } catch {
      setError("网络连接失败，请稍后重试");
    } finally {
      setLoading(false);
    }
  }

  return (
    <>
      <button className={className ?? styles.trigger} type="button" onClick={() => setOpen(true)}>{triggerLabel}</button>
      {open && (
        <div className={styles.backdrop} onMouseDown={(event) => event.target === event.currentTarget && setOpen(false)}>
          <div className={styles.dialog} ref={dialogRef} role="dialog" aria-modal="true" aria-labelledby="login-dialog-title">
            <button className={styles.closeButton} type="button" onClick={() => setOpen(false)} aria-label="关闭登录窗口">×</button>
            <div className={styles.dialogTop}><span>登录 NOVA 企业商城</span><Link href="/merchant/apply">企业用户入驻 →</Link></div>
            <div className={styles.dialogBody}>
              <section className={styles.safePanel}>
                <h2>安全便捷登录</h2>
                <div className={styles.safeVisual}><CommerceIcon name="account" size={156} largeSource priority /></div>
                <strong>NOVA MEMBER</strong>
                <p>统一账号登录，采购信息加密保护</p>
                <div><span>✓</span> 企业专价　<span>✓</span> 订单管理　<span>✓</span> 智能客服</div>
              </section>
              <section className={styles.passwordPanel}>
                <div className={styles.tabs}><strong id="login-dialog-title">密码登录</strong><Link href="/register">免费注册</Link></div>
                <form onSubmit={submit} className={styles.form}>
                  <label><span>邮</span><input name="email" type="email" maxLength={254} autoComplete="email" aria-label="邮箱" placeholder="请输入邮箱账号" required /></label>
                  <label><span>密</span><input name="password" type="password" minLength={8} maxLength={72} autoComplete="current-password" aria-label="密码" placeholder="请输入密码" required /></label>
                  <div className={styles.formMeta}><span>请勿在公共设备保存密码</span><a href="mailto:support@nova.example">忘记密码</a></div>
                  {error && <div className={styles.error} role="alert">{error}</div>}
                  <button className={styles.submitButton} type="submit" disabled={loading}>{loading ? "登录中…" : "登 录"}</button>
                </form>
                <div className={styles.panelFooter}><span>HttpOnly 安全会话保护</span><Link href="/register">立即注册 →</Link></div>
              </section>
            </div>
          </div>
        </div>
      )}
    </>
  );
}
