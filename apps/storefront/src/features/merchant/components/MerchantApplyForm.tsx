"use client";

import { FormEvent, useState } from "react";
import Link from "next/link";
import { CommerceIcon } from "@/shared/ui/CommerceIcon";
import styles from "./merchantApply.module.css";

type State = "idle" | "submitting" | "success" | "error";

export function MerchantApplyForm() {
  const [state, setState] = useState<State>("idle");
  const [message, setMessage] = useState("");

  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault(); setState("submitting"); setMessage("");
    const form = new FormData(event.currentTarget);
    const payload = Object.fromEntries(form.entries());
    try {
      const response = await fetch(`${process.env.NEXT_PUBLIC_COMMERCE_API_URL ?? "http://localhost:8080"}/api/public/merchant-applications`, { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(payload) });
      if (!response.ok) throw new Error("提交失败，请核对资料后重试");
      setState("success"); setMessage("入驻申请已提交，平台将在 1–3 个工作日内完成审核。"); event.currentTarget.reset();
    } catch (error) { setState("error"); setMessage(error instanceof Error ? error.message : "暂时无法提交"); }
  }

  return <main className={styles.page}><section className={styles.intro}><Link href="/" className={styles.brand}>NOVA · 商家中心</Link><span>MARKETPLACE</span><h1>与优质企业客户，<br />建立长期生意。</h1><p>统一商品、订单、履约、结算和智能客服能力，让商家专注于商品与服务。</p><div className={styles.steps}>{["提交企业资质", "平台审核", "创建店铺", "发布商品"].map((step, index) => <div key={step}><b>{index + 1}</b><span>{step}</span></div>)}</div><CommerceIcon name="store" size={180} largeSource /></section><section className={styles.formPanel}><div><small>第三方商家入驻</small><h2>填写企业与店铺资料</h2><p>当前阶段不收取保证金，审核通过后再配置结算账户。</p></div><form onSubmit={submit}><label>企业法定名称<input name="legalName" required placeholder="营业执照上的企业名称" /></label><label>拟用店铺名称<input name="storeName" required placeholder="例如：NOVA 数字办公旗舰店" /></label><div className={styles.row}><label>联系人<input name="contactName" required /></label><label>联系电话<input name="contactPhone" required inputMode="tel" /></label></div><label>统一社会信用代码 / 注册号<input name="businessLicenseNo" required /></label><label className={styles.agree}><input type="checkbox" required /> 我已阅读并同意平台入驻与数据处理规则</label><button disabled={state === "submitting"}>{state === "submitting" ? "正在提交…" : "提交入驻申请"}</button>{message && <p className={state === "success" ? styles.success : styles.error}>{message}</p>}</form></section></main>;
}
