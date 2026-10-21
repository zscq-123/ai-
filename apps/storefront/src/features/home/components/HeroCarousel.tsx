"use client";

import Image from "next/image";
import Link from "next/link";
import { KeyboardEvent, useEffect, useState } from "react";
import styles from "./home.module.css";

const slides = [
  {
    image: "/brand/banners/nova-enterprise-hero.png",
    alt: "NOVA 企业采购精选办公与数码商品",
    tag: "NOVA 企业采购季",
    title: <>企业焕新，<br />采购更省心</>,
    description: "品牌直供 · 批量优惠 · 极速履约",
    action: "立即采购",
    href: "#recommend",
    shade: "linear-gradient(90deg,rgba(104,0,5,.76) 0%,rgba(118,0,5,.3) 48%,transparent 72%)",
  },
  {
    image: "/brand/banners/nova-digital-office-hero-v1.png",
    alt: "NOVA 数字办公设备采购专题",
    tag: "数字办公焕新",
    title: <>协作升级，<br />效率全面在线</>,
    description: "商用终端 · 会议设备 · 办公耗材",
    action: "进入会场",
    href: "/office",
    shade: "linear-gradient(90deg,rgba(4,18,43,.88) 0%,rgba(5,22,52,.5) 48%,transparent 72%)",
  },
  {
    image: "/brand/banners/nova-industrial-delivery-hero-v1.png",
    alt: "NOVA 工业品与企业履约专题",
    tag: "极速履约计划",
    title: <>工业好货，<br />按时送达</>,
    description: "品牌直供 · 仓配协同 · 售后保障",
    action: "采购工业品",
    href: "/industrial",
    shade: "linear-gradient(90deg,rgba(74,0,3,.88) 0%,rgba(96,4,8,.45) 48%,transparent 72%)",
  },
];

export function HeroCarousel() {
  const [active, setActive] = useState(0);
  const [paused, setPaused] = useState(false);
  const [reduceMotion, setReduceMotion] = useState(false);

  useEffect(() => {
    const query = window.matchMedia("(prefers-reduced-motion: reduce)");
    const updatePreference = () => setReduceMotion(query.matches);
    updatePreference();
    query.addEventListener("change", updatePreference);
    return () => query.removeEventListener("change", updatePreference);
  }, []);

  useEffect(() => {
    if (paused || reduceMotion) return;
    const timer = window.setInterval(() => setActive((current) => (current + 1) % slides.length), 5000);
    return () => window.clearInterval(timer);
  }, [paused, reduceMotion]);

  const move = (direction: number) => setActive((current) => (current + direction + slides.length) % slides.length);
  const handleKeyDown = (event: KeyboardEvent<HTMLElement>) => {
    if (event.key === "ArrowLeft") { event.preventDefault(); move(-1); }
    if (event.key === "ArrowRight") { event.preventDefault(); move(1); }
  };

  return (
    <section
      className={styles.heroBanner}
      aria-label="商城活动轮播"
      aria-roledescription="轮播图"
      tabIndex={0}
      onKeyDown={handleKeyDown}
      onMouseEnter={() => setPaused(true)}
      onMouseLeave={() => setPaused(false)}
      onFocusCapture={() => setPaused(true)}
      onBlurCapture={(event) => { if (!event.currentTarget.contains(event.relatedTarget)) setPaused(false); }}
    >
      {slides.map((slide, index) => (
        <article className={`${styles.heroSlide} ${index === active ? styles.heroSlideActive : ""}`} aria-hidden={index !== active} key={slide.image}>
          <Image className={styles.heroImage} src={slide.image} alt={index === active ? slide.alt : ""} fill priority sizes="(max-width: 900px) 100vw, 60vw" />
          <div className={styles.heroShade} style={{ background: slide.shade }} />
          <div className={styles.heroCopy}>
            <span className={styles.heroTag}>{slide.tag}</span>
            <h1>{slide.title}</h1>
            <p>{slide.description}</p>
            <Link href={slide.href} tabIndex={index === active ? 0 : -1}>{slide.action} <span>→</span></Link>
          </div>
        </article>
      ))}
      <button className={`${styles.sliderArrow} ${styles.sliderPrevious}`} type="button" aria-label="上一张" onClick={() => move(-1)}>‹</button>
      <button className={`${styles.sliderArrow} ${styles.sliderNext}`} type="button" aria-label="下一张" onClick={() => move(1)}>›</button>
      <div className={styles.sliderDots} aria-label={`当前第 ${active + 1} 张，共 ${slides.length} 张`}>
        {slides.map((slide, index) => <button className={index === active ? styles.sliderDotActive : undefined} type="button" aria-label={`切换到第 ${index + 1} 张：${slide.tag}`} aria-current={index === active ? "true" : undefined} onClick={() => setActive(index)} key={slide.image} />)}
      </div>
    </section>
  );
}
