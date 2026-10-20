"use client";

import { FormEvent, useState } from "react";
import { CommerceIcon } from "@/shared/ui/CommerceIcon";
import styles from "./supportWidget.module.css";

type Message = { role: "user" | "assistant"; content: string; citations?: Array<{ title: string; reference: string }> };

export function SupportWidget() {
  const [open, setOpen] = useState(false); const [loading, setLoading] = useState(false);
  const [messages, setMessages] = useState<Message[]>([{ role: "assistant", content: "你好，我是 NOVA AI 客服。可以帮你了解商品、配送和平台规则。" }]);
  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault(); const form=new FormData(event.currentTarget); const content=String(form.get("message") ?? "").trim(); if (!content) return;
    setMessages((current)=>[...current,{role:"user",content}]); setLoading(true); event.currentTarget.reset();
    try { const response=await fetch(`${process.env.NEXT_PUBLIC_AI_SERVICE_URL ?? "http://localhost:8000"}/v1/support/chat`,{method:"POST",headers:{"Content-Type":"application/json"},body:JSON.stringify({message:content})}); if(!response.ok) throw new Error(); const data=await response.json() as {answer:string;citations:Message["citations"]}; setMessages((current)=>[...current,{role:"assistant",content:data.answer,citations:data.citations}]); }
    catch { setMessages((current)=>[...current,{role:"assistant",content:"服务暂时不可用，我已保留问题，请稍后重试或转人工。"}]); } finally { setLoading(false); }
  }
  return <><button className={styles.trigger} aria-label="联系 AI 客服" onClick={()=>setOpen(true)}><CommerceIcon name="aiSupport" size={48} largeSource /><span>AI 客服</span></button>{open&&<aside className={styles.panel} aria-label="AI 客服对话"><header><div><CommerceIcon name="aiSupport" size={44} largeSource /><div><strong>NOVA AI 客服</strong><span>在线 · 回答附带来源</span></div></div><button onClick={()=>setOpen(false)} aria-label="关闭">×</button></header><div className={styles.messages}>{messages.map((message,index)=><div className={message.role==="user"?styles.user:styles.assistant} key={index}><p>{message.content}</p>{message.citations?.map((citation)=><small key={citation.reference}>来源：{citation.title}</small>)}</div>)}{loading&&<div className={styles.assistant}><p>正在查找可靠信息…</p></div>}</div><form onSubmit={submit}><input name="message" aria-label="输入问题" placeholder="询问商品、配送或售后规则" autoComplete="off"/><button>发送</button></form><footer>退款、取消等资金操作必须登录并再次确认</footer></aside>}</>;
}
