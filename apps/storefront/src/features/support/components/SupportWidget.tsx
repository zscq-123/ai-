"use client";

import { FormEvent, useEffect, useState } from "react";
import Link from "next/link";
import { CommerceIcon } from "@/shared/ui/CommerceIcon";
import styles from "./supportWidget.module.css";

type Citation = { title: string; reference: string };
type Message = { role: "user" | "assistant"; content: string; citations?: Citation[] };
type FaqCard = { id: string; question: string };

const FALLBACK_FAQS: FaqCard[] = [
  { id: "delivery", question: "多久发货？" },
  { id: "invoice", question: "能开发票吗？" },
  { id: "shipping", question: "包邮吗？" },
  { id: "return", question: "怎么申请退货？" },
];

type SupportWidgetProps = {
  merchantId?: string;
  productId?: string;
  skuId?: string;
};

export function SupportWidget({ merchantId, productId, skuId }: SupportWidgetProps) {
  const [open, setOpen] = useState(false);
  const [loading, setLoading] = useState(false);
  const [faqCards, setFaqCards] = useState<FaqCard[]>(FALLBACK_FAQS);
  const [messages, setMessages] = useState<Message[]>([
    { role: "assistant", content: "你好，我是 NOVA AI 客服。你可以先选择常见问题，也可以直接输入。" },
  ]);

  useEffect(() => {
    const openSupport = () => setOpen(true);
    window.addEventListener("nova:open-support", openSupport);
    return () => window.removeEventListener("nova:open-support", openSupport);
  }, []);

  useEffect(() => {
    const controller = new AbortController();
    const query = merchantId ? `?merchantId=${encodeURIComponent(merchantId)}` : "";
    fetch(`/api/support/faqs${query}`, { signal: controller.signal, cache: "no-store" })
      .then(async (response) => response.ok ? response.json() as Promise<unknown> : [])
      .then((payload) => {
        if (!Array.isArray(payload)) return;
        const cards = payload.flatMap((item): FaqCard[] => {
          if (!item || typeof item !== "object") return [];
          const value = item as { id?: unknown; question?: unknown };
          return typeof value.id === "string" && typeof value.question === "string"
            ? [{ id: value.id, question: value.question }]
            : [];
        }).slice(0, 6);
        if (cards.length) setFaqCards(cards);
      })
      .catch(() => undefined);
    return () => controller.abort();
  }, [merchantId]);

  async function ask(content: string) {
    const question = content.trim();
    if (!question || loading) return;
    setMessages((current) => [...current, { role: "user", content: question }]);
    setLoading(true);
    try {
      const response = await fetch("/api/support/chat", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ message: question, merchantId, productId, skuId }),
      });
      if (!response.ok) throw new Error();
      const data = await response.json() as { answer: string; citations?: Citation[] };
      setMessages((current) => [
        ...current,
        { role: "assistant", content: data.answer, citations: data.citations },
      ]);
    } catch {
      setMessages((current) => [
        ...current,
        { role: "assistant", content: "服务暂时不可用，这次问题还没有提交成功。请稍后重试或联系人工客服。" },
      ]);
    } finally {
      setLoading(false);
    }
  }

  function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const form = new FormData(event.currentTarget);
    const content = String(form.get("message") ?? "");
    event.currentTarget.reset();
    void ask(content);
  }

  return <>
    <nav className={styles.rail} aria-label="快捷服务">
      <button className={styles.railButton} type="button" aria-label="联系 AI 客服" aria-expanded={open} onClick={() => setOpen((current) => !current)}>
        <CommerceIcon name="aiSupport" size={46} largeSource />
        <span>客服</span>
      </button>
      <Link className={styles.railButton} href="/cart" aria-label="打开购物车">
        <CommerceIcon name="cart" size={46} largeSource />
        <span>购物车</span>
      </Link>
    </nav>
    {open && <aside className={styles.panel} aria-label="AI 客服对话">
      <header>
        <div><CommerceIcon name="aiSupport" size={44} largeSource /><div><strong>NOVA AI 客服</strong><span>在线 · 回答附带来源</span></div></div>
        <button onClick={() => setOpen(false)} aria-label="关闭">×</button>
      </header>
      <div className={styles.messages}>
        {messages.map((message, index) => <div className={message.role === "user" ? styles.user : styles.assistant} key={`${message.role}-${index}`}>
          <p>{message.content}</p>
          {message.citations?.map((citation) => <small key={citation.reference}>来源：{citation.title}</small>)}
        </div>)}
        <section className={styles.faqCard} aria-label="常见 F&A">
          <div><strong>常见 F&amp;A</strong><span>点击问题立即查看回答</span></div>
          <div className={styles.faqGrid}>{faqCards.map((faq) => <button type="button" key={faq.id} disabled={loading} onClick={() => void ask(faq.question)}>{faq.question}</button>)}</div>
        </section>
        {loading && <div className={styles.assistant}><p>正在查找可靠信息…</p></div>}
      </div>
      <form onSubmit={submit}><input name="message" aria-label="输入问题" placeholder="询问商品、配送或售后规则" autoComplete="off"/><button disabled={loading}>发送</button></form>
      <footer>退款资金操作转人工；订单变更需登录并再次确认</footer>
    </aside>}
  </>;
}
