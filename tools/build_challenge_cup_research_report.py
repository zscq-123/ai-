#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Build the Challenge Cup research report for the NOVA customer-service system."""

from __future__ import annotations

import math
import os
import re
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont
from docx import Document
from docx.enum.section import WD_SECTION
from docx.enum.table import WD_CELL_VERTICAL_ALIGNMENT, WD_TABLE_ALIGNMENT
from docx.enum.text import WD_ALIGN_PARAGRAPH, WD_BREAK, WD_LINE_SPACING
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from docx.shared import Cm, Mm, Pt, RGBColor


ROOT = Path(__file__).resolve().parents[1]
OUT_DIR = ROOT / "outputs"
ASSET_DIR = ROOT / ".tmp_challenge_report_assets"
OUT = OUT_DIR / "NOVA_AI客服研究报告_挑战杯修订版.docx"

SCREEN_OMS = ROOT / "data/deployment-154-20261106/public-acceptance/oms-privacy.png"
SCREEN_SITE = ROOT / "data/deployment-154-20261106/public-acceptance/shop-injection.png"

FONT_SANS = Path(
    "/System/Library/AssetsV2/com_apple_MobileAsset_Font8/"
    "86ba2c91f017a3749571a82f2c6d890ac7ffb2fb.asset/AssetData/PingFang.ttc"
)
FONT_SONG = Path("/System/Library/Fonts/Supplemental/Songti.ttc")
FONT_HEI = Path("/System/Library/Fonts/STHeiti Medium.ttc")
FONT_LATIN = Path("/System/Library/Fonts/Supplemental/Arial.ttf")

INK = "#111827"
GREY = "#4B5563"
MUTED = "#6B7280"
LIGHT = "#F3F4F6"
BLUE = "#173B6C"
BLUE2 = "#2563A6"
BLUEF = "#DCEAF7"
GREEN = "#177245"
GREENF = "#DCF1E5"
AMBER = "#A66100"
AMBERF = "#F9E8C5"
RED = "#A43A3A"
REDF = "#F6DFDF"
WHITE = "#FFFFFF"
BORDER = "#D9D9D9"


def pil_font(size: int, bold: bool = False) -> ImageFont.FreeTypeFont:
    path = FONT_HEI if bold else FONT_SANS
    return ImageFont.truetype(str(path), size=size, index=0)


def wrap_text(draw: ImageDraw.ImageDraw, text: str, font, max_width: int) -> list[str]:
    lines: list[str] = []
    for paragraph in text.split("\n"):
        if not paragraph:
            lines.append("")
            continue
        current = ""
        for ch in paragraph:
            candidate = current + ch
            if draw.textbbox((0, 0), candidate, font=font)[2] <= max_width:
                current = candidate
            else:
                if current:
                    lines.append(current)
                current = ch
        if current:
            lines.append(current)
    return lines


def draw_wrapped(
    draw: ImageDraw.ImageDraw,
    xy: tuple[int, int],
    text: str,
    font,
    fill: str,
    max_width: int,
    line_gap: int = 8,
    anchor: str | None = None,
) -> int:
    x, y = xy
    lines = wrap_text(draw, text, font, max_width)
    line_h = font.size + line_gap
    for line in lines:
        if anchor == "mm":
            draw.text((x, y), line, font=font, fill=fill, anchor="mm")
        else:
            draw.text((x, y), line, font=font, fill=fill)
        y += line_h
    return y


def rounded_box(draw, box, fill, outline, radius=24, width=3):
    draw.rounded_rectangle(box, radius=radius, fill=fill, outline=outline, width=width)


def arrow(draw, start, end, color=BLUE2, width=6):
    draw.line([start, end], fill=color, width=width)
    ang = math.atan2(end[1] - start[1], end[0] - start[0])
    length = 18
    spread = 0.55
    p1 = (
        end[0] - length * math.cos(ang - spread),
        end[1] - length * math.sin(ang - spread),
    )
    p2 = (
        end[0] - length * math.cos(ang + spread),
        end[1] - length * math.sin(ang + spread),
    )
    draw.polygon([end, p1, p2], fill=color)


def save_canvas(img: Image.Image, name: str) -> Path:
    path = ASSET_DIR / name
    img.save(path, dpi=(200, 200))
    return path


def make_cover_graphic() -> Path:
    img = Image.new("RGB", (1600, 560), WHITE)
    d = ImageDraw.Draw(img)
    title = pil_font(46, True)
    body = pil_font(28, False)
    small = pil_font(24, False)

    cards = [
        (310, 55, 1290, 335, "NOVA AI 客服", "意图路由  混合检索  业务工具\n多 Agent 协作  独立审核  人工接管", GREENF, GREEN),
        (150, 390, 650, 505, "OMS 验证媒介", "后台身份与订单场景", BLUEF, BLUE),
        (950, 390, 1450, 505, "独立站验证媒介", "访客与客户服务场景", AMBERF, AMBER),
    ]
    for x1, y1, x2, y2, heading, text, fill, outline in cards:
        rounded_box(d, (x1, y1, x2, y2), fill, outline, 30, 4)
        d.text(((x1 + x2) // 2, y1 + 58), heading, font=title if y1 < 100 else pil_font(31, True), fill=INK, anchor="mm")
        yy = y1 + (135 if y1 < 100 else 88)
        for line in text.split("\n"):
            d.text(((x1 + x2) // 2, yy), line, font=body, fill=GREY, anchor="mm")
            yy += 48
    arrow(d, (650, 350), (470, 382), BLUE2, 7)
    arrow(d, (950, 350), (1130, 382), BLUE2, 7)
    d.text((800, 545), "研究对象是 AI 客服核心  OMS 与独立站仅用于接入和验证", font=small, fill=MUTED, anchor="mm")
    return save_canvas(img, "cover-system.png")


def make_survey_chart() -> Path:
    labels = [
        "咨询商品功能规格",
        "希望快速解决常见问题",
        "希望准确查订单物流",
        "希望立即处理高风险转人工",
        "可接受仅答复或确认后办理",
        "关注准确不猜测",
    ]
    values = [90, 70, 65, 80, 90, 60]
    img = Image.new("RGB", (1600, 900), WHITE)
    d = ImageDraw.Draw(img)
    title = pil_font(40, True)
    label_font = pil_font(28, False)
    value_font = pil_font(28, True)
    d.text((800, 55), "客户需求调研关键结果", font=title, fill=INK, anchor="mm")
    left = 420
    top = 145
    bar_h = 76
    gap = 42
    scale = 9.0
    for i, (label, value) in enumerate(zip(labels, values)):
        y = top + i * (bar_h + gap)
        d.text((left - 28, y + bar_h / 2), label, font=label_font, fill=INK, anchor="rm")
        rounded_box(d, (left, y, left + 900, y + bar_h), LIGHT, LIGHT, 18, 0)
        rounded_box(d, (left, y, left + value * scale, y + bar_h), BLUEF, BLUE2, 18, 3)
        d.text((left + value * scale - 20, y + bar_h / 2), f"{value}%", font=value_font, fill=BLUE, anchor="rm")
    d.text((800, 850), "样本 21 份 其中客户 20 份 企业 1 份  企业样本不用于推算行业比例", font=pil_font(24), fill=MUTED, anchor="mm")
    return save_canvas(img, "survey-results.png")


def make_challenge_chain() -> Path:
    img = Image.new("RGB", (1600, 760), WHITE)
    d = ImageDraw.Draw(img)
    title = pil_font(40, True)
    head = pil_font(31, True)
    body = pil_font(25, False)
    d.text((800, 55), "AI 客服三层科学挑战", font=title, fill=INK, anchor="mm")
    boxes = [
        (80, 180, 480, 590, "数据层", "静态政策与实时订单并存\n来源身份与时间有效性不同\n跨站知识不可混用", BLUEF, BLUE),
        (600, 180, 1000, 590, "算法层", "检索召回与拒答边界并重\n模型必须调用正确工具\n答案逐条接受证据审核", GREENF, GREEN),
        (1120, 180, 1520, 590, "系统层", "身份与商户范围可信传递\n多 Agent 延迟与降级控制\n人工接管与审计闭环", AMBERF, AMBER),
    ]
    for x1, y1, x2, y2, h, text, fill, outline in boxes:
        rounded_box(d, (x1, y1, x2, y2), fill, outline, 30, 4)
        d.text(((x1 + x2)//2, y1 + 75), h, font=head, fill=INK, anchor="mm")
        yy = y1 + 150
        for line in text.split("\n"):
            d.text(((x1 + x2)//2, yy), line, font=body, fill=GREY, anchor="mm")
            yy += 62
    arrow(d, (490, 385), (585, 385), BLUE2, 7)
    arrow(d, (1010, 385), (1105, 385), BLUE2, 7)
    d.text((800, 690), "动态事实可信  →  生成过程可控  →  跨系统服务可运营", font=pil_font(29, True), fill=BLUE, anchor="mm")
    return save_canvas(img, "scientific-challenges.png")


def make_architecture() -> Path:
    img = Image.new("RGB", (1600, 1020), WHITE)
    d = ImageDraw.Draw(img)
    title = pil_font(40, True)
    head = pil_font(28, True)
    body = pil_font(23, False)
    d.text((800, 55), "NOVA AI 客服核心技术架构", font=title, fill=INK, anchor="mm")

    layers = [
        (80, 125, 1520, 265, "验证媒介层", ["OMS 管理端", "独立站客服组件", "可扩展渠道与工单"]),
        (80, 315, 1520, 485, "可信网关层", ["JWT 与订单归属", "HMAC-SHA256 签名", "来源与商户隔离"]),
        (80, 535, 1520, 755, "AI 客服核心层", ["意图路由与混合检索", "知识 订单 售后 Agent", "独立审核与确定性摘要"]),
        (80, 805, 1520, 955, "证据层", ["FAQ 与政策", "库存 订单 物流 支付", "引用与审计记录"]),
    ]
    fills = [BLUEF, LIGHT, GREENF, AMBERF]
    outlines = [BLUE, GREY, GREEN, AMBER]
    for idx, (x1, y1, x2, y2, label, items) in enumerate(layers):
        rounded_box(d, (x1, y1, x2, y2), fills[idx], outlines[idx], 26, 3)
        d.text((x1 + 120, (y1+y2)//2), label, font=head, fill=INK, anchor="mm")
        inner_left = x1 + 260
        item_w = (x2 - inner_left - 70) / 3
        for j, item in enumerate(items):
            bx1 = int(inner_left + j * item_w + 10)
            bx2 = int(inner_left + (j + 1) * item_w - 15)
            rounded_box(d, (bx1, y1 + 28, bx2, y2 - 28), WHITE, BORDER, 18, 2)
            d.text(((bx1+bx2)//2, (y1+y2)//2), item, font=body, fill=INK, anchor="mm")
        if idx < len(layers)-1:
            arrow(d, (800, y2 + 8), (800, layers[idx+1][1] - 10), BLUE2, 6)
    return save_canvas(img, "system-architecture.png")


def make_evidence_flow() -> Path:
    img = Image.new("RGB", (1600, 870), WHITE)
    d = ImageDraw.Draw(img)
    d.text((800, 55), "可信证据与最小数据流", font=pil_font(40, True), fill=INK, anchor="mm")
    head = pil_font(28, True)
    body = pil_font(23)
    cols = [
        (60, 180, 340, 650, "业务后端", ["校验身份", "校验订单归属", "过滤姓名电话地址", "生成签名证据"]),
        (470, 180, 750, 650, "集成网关", ["校验时间窗", "校验 HMAC", "绑定 source", "拒绝额外身份字段"]),
        (880, 180, 1160, 650, "NOVA", ["限定证据范围", "调用只读工具", "生成带引用回答", "无证据时拒答或转人工"]),
        (1290, 180, 1570, 650, "用户端", ["获得答案", "查看来源", "高风险需确认", "必要时进入人工工单"]),
    ]
    fills = [BLUEF, LIGHT, GREENF, AMBERF]
    outlines = [BLUE, GREY, GREEN, AMBER]
    for idx, (x1, y1, x2, y2, h, lines) in enumerate(cols):
        rounded_box(d, (x1, y1, x2, y2), fills[idx], outlines[idx], 28, 4)
        d.text(((x1+x2)//2, y1+65), h, font=head, fill=INK, anchor="mm")
        yy = y1 + 150
        for line in lines:
            d.ellipse((x1+40, yy-9, x1+58, yy+9), fill=outlines[idx])
            d.text((x1+78, yy), line, font=body, fill=GREY, anchor="lm")
            yy += 78
        if idx < len(cols)-1:
            arrow(d, (x2+15, 415), (cols[idx+1][0]-15, 415), BLUE2, 6)
    d.text((800, 770), "浏览器不持有签名密钥  订单证据只包含订单号 状态 金额 币种", font=pil_font(27, True), fill=RED, anchor="mm")
    d.text((800, 820), "未取得物流轨迹或退款到账记录时 系统明确说明无法确认", font=pil_font(24), fill=MUTED, anchor="mm")
    return save_canvas(img, "evidence-flow.png")


def make_agent_flow() -> Path:
    img = Image.new("RGB", (1600, 930), WHITE)
    d = ImageDraw.Draw(img)
    title = pil_font(40, True)
    head = pil_font(27, True)
    body = pil_font(22)
    d.text((800, 50), "多 Agent 协作与独立审核", font=title, fill=INK, anchor="mm")
    nodes = {
        "input": (600, 115, 1000, 235, "可信请求与本轮证据", BLUEF, BLUE),
        "plan": (600, 300, 1000, 430, "主 Agent\n拆分任务与声明依赖", LIGHT, GREY),
        "knowledge": (80, 515, 430, 690, "知识 Agent\nsearch_knowledge", BLUEF, BLUE),
        "order": (625, 515, 975, 690, "订单 Agent\nread_order", GREENF, GREEN),
        "after": (1170, 515, 1520, 690, "售后 Agent\npolicy + order result", AMBERF, AMBER),
        "review": (600, 770, 1000, 885, "审核 Agent\n只通过或拒绝 不改写事实", REDF, RED),
    }
    for x1, y1, x2, y2, text, fill, outline in nodes.values():
        rounded_box(d, (x1, y1, x2, y2), fill, outline, 26, 4)
        lines = text.split("\n")
        yy = (y1+y2)//2 - (len(lines)-1)*24
        for i, line in enumerate(lines):
            d.text(((x1+x2)//2, yy+i*52), line, font=head if i==0 else body, fill=INK, anchor="mm")
    arrow(d, (800, 245), (800, 285), BLUE2, 6)
    arrow(d, (730, 440), (320, 500), BLUE2, 6)
    arrow(d, (800, 440), (800, 500), BLUE2, 6)
    arrow(d, (870, 440), (1280, 500), BLUE2, 6)
    arrow(d, (965, 600), (1155, 600), AMBER, 6)
    d.text((1060, 575), "订单证据", font=body, fill=AMBER, anchor="mm")
    for x in (255, 800, 1345):
        arrow(d, (x, 705), (735 if x < 800 else 800 if x == 800 else 865, 755), BLUE2, 5)
    return save_canvas(img, "agent-flow.png")


def make_retrieval_chart() -> Path:
    labels = ["关键词检索", "向量检索", "意图路由加检索降级"]
    vals = [55.5, 76.0, 97.0]
    colors = [GREY, BLUE2, GREEN]
    fills = [LIGHT, BLUEF, GREENF]
    img = Image.new("RGB", (1600, 880), WHITE)
    d = ImageDraw.Draw(img)
    d.text((800, 55), "冻结保留集检索首条命中率", font=pil_font(40, True), fill=INK, anchor="mm")
    base_y = 730
    left = 210
    bar_w = 280
    gap = 170
    scale = 5.5
    for i, (label, value) in enumerate(zip(labels, vals)):
        x = left + i*(bar_w+gap)
        h = int(value*scale)
        rounded_box(d, (x, base_y-h, x+bar_w, base_y), fills[i], colors[i], 24, 4)
        d.text((x+bar_w/2, base_y-h-42), f"{value:.1f}%", font=pil_font(34, True), fill=colors[i], anchor="mm")
        for j, line in enumerate(wrap_text(d, label, pil_font(26), bar_w+50)):
            d.text((x+bar_w/2, base_y+55+j*36), line, font=pil_font(26), fill=INK, anchor="mm")
    d.line((160, base_y, 1450, base_y), fill=BORDER, width=3)
    d.text((800, 830), "200 条冻结保留集  含 40 条应拒绝问题  应拒绝准确率 100.0%", font=pil_font(24), fill=MUTED, anchor="mm")
    return save_canvas(img, "retrieval-comparison.png")


def make_evaluation_chart() -> Path:
    labels = ["45 条对话回归", "核心安全 200 条", "独立回归 300 条", "独立回归多轮"]
    vals = [100.0, 100.0, 93.3, 80.0]
    notes = ["45/45", "200/200", "280/300", "80/100"]
    colors = [BLUE, GREEN, BLUE2, AMBER]
    fills = [BLUEF, GREENF, BLUEF, AMBERF]
    img = Image.new("RGB", (1600, 860), WHITE)
    d = ImageDraw.Draw(img)
    d.text((800, 55), "阶段性评测结果", font=pil_font(40, True), fill=INK, anchor="mm")
    left = 430
    top = 160
    width = 950
    for i, (label, value, note) in enumerate(zip(labels, vals, notes)):
        y = top + i*150
        d.text((left-30, y+38), label, font=pil_font(28), fill=INK, anchor="rm")
        rounded_box(d, (left, y, left+width, y+76), LIGHT, LIGHT, 20, 0)
        rounded_box(d, (left, y, left+int(width*value/100), y+76), fills[i], colors[i], 20, 3)
        d.text((left+int(width*value/100)-18, y+38), f"{value:.1f}%  {note}", font=pil_font(27, True), fill=colors[i], anchor="rm")
    d.text((800, 800), "不同评测集不能简单合并  多轮对话仍是下一阶段主要短板", font=pil_font(25), fill=RED, anchor="mm")
    return save_canvas(img, "evaluation-results.png")


def make_validation_timeline() -> Path:
    img = Image.new("RGB", (1600, 840), WHITE)
    d = ImageDraw.Draw(img)
    d.text((800, 55), "从离线评测到跨系统联调的证据链", font=pil_font(40, True), fill=INK, anchor="mm")
    y = 420
    d.line((150, y, 1450, y), fill=BLUE2, width=8)
    items = [
        (220, "需求调研", "21 份反馈\n确定准确 安全 转人工"),
        (520, "检索与安全", "200 条检索保留集\n200 条安全集"),
        (820, "真实工具验收", "隔离数据库\n12 项全部通过"),
        (1120, "本地浏览器抽测", "15 通过 5 部分 4 未过\n定位多轮与英文短板"),
        (1400, "公网修复验收", "222 项 AI 测试\n21 项浏览器检查"),
    ]
    for idx, (x, head, desc) in enumerate(items):
        color = [BLUE, GREEN, AMBER, RED, GREEN][idx]
        fill = [BLUEF, GREENF, AMBERF, REDF, GREENF][idx]
        d.ellipse((x-30, y-30, x+30, y+30), fill=WHITE, outline=color, width=8)
        above = idx % 2 == 0
        box = (x-150, y-260, x+150, y-75) if above else (x-150, y+75, x+150, y+300)
        rounded_box(d, box, fill, color, 24, 3)
        yy = box[1]+45
        d.text((x, yy), head, font=pil_font(26, True), fill=INK, anchor="mm")
        yy += 58
        for line in desc.split("\n"):
            d.text((x, yy), line, font=pil_font(20), fill=GREY, anchor="mm")
            yy += 36
    return save_canvas(img, "validation-timeline.png")


def make_roadmap() -> Path:
    img = Image.new("RGB", (1600, 900), WHITE)
    d = ImageDraw.Draw(img)
    d.text((800, 55), "下一阶段研究与转化路线", font=pil_font(40, True), fill=INK, anchor="mm")
    phases = [
        (80, 170, 430, 720, "阶段一", "真实企业基线", ["接入正式 FAQ 与商品", "建立人工工单基线", "收集脱敏真实会话"], BLUEF, BLUE),
        (480, 170, 830, 720, "阶段二", "生产等价验证", ["多租户越权专项", "共享会话存储", "压力与故障演练"], GREENF, GREEN),
        (880, 170, 1230, 720, "阶段三", "效果对照试验", ["A B 对照与盲审", "解决率 满意度 成本", "统计显著性与误差分析"], AMBERF, AMBER),
        (1280, 170, 1550, 720, "阶段四", "成果固化", ["专利与软著", "企业试点报告", "竞赛演示与答辩"], REDF, RED),
    ]
    for i, (x1,y1,x2,y2,p,h,lines,fill,outline) in enumerate(phases):
        rounded_box(d, (x1,y1,x2,y2), fill, outline, 28, 4)
        d.text(((x1+x2)//2,y1+58), p, font=pil_font(24, True), fill=outline, anchor="mm")
        d.text(((x1+x2)//2,y1+125), h, font=pil_font(29, True), fill=INK, anchor="mm")
        yy=y1+230
        for line in lines:
            d.text(((x1+x2)//2,yy), line, font=pil_font(22), fill=GREY, anchor="mm")
            yy+=90
        if i < len(phases)-1:
            arrow(d,(x2+10,445),(phases[i+1][0]-10,445),BLUE2,6)
    d.text((800, 825), "核心原则 先补齐真实企业基线 再计算成本节约和转化收益", font=pil_font(27, True), fill=RED, anchor="mm")
    return save_canvas(img, "future-roadmap.png")


def make_equation(text: str, name: str, subtitle: str) -> Path:
    img = Image.new("RGB", (1600, 300), WHITE)
    d = ImageDraw.Draw(img)
    d.text((800, 120), text, font=ImageFont.truetype(str(FONT_LATIN), 54), fill=INK, anchor="mm")
    d.text((800, 235), subtitle, font=pil_font(23), fill=MUTED, anchor="mm")
    return save_canvas(img, name)


def set_repeat_table_header(row):
    tr_pr = row._tr.get_or_add_trPr()
    tbl_header = OxmlElement("w:tblHeader")
    tbl_header.set(qn("w:val"), "true")
    tr_pr.append(tbl_header)


def set_cell_shading(cell, fill: str):
    tc_pr = cell._tc.get_or_add_tcPr()
    shd = tc_pr.find(qn("w:shd"))
    if shd is None:
        shd = OxmlElement("w:shd")
        tc_pr.append(shd)
    shd.set(qn("w:fill"), fill.replace("#", ""))


def set_cell_margins(cell, top=90, start=100, bottom=90, end=100):
    tc = cell._tc
    tc_pr = tc.get_or_add_tcPr()
    tc_mar = tc_pr.first_child_found_in("w:tcMar")
    if tc_mar is None:
        tc_mar = OxmlElement("w:tcMar")
        tc_pr.append(tc_mar)
    for m, v in (("top", top), ("start", start), ("bottom", bottom), ("end", end)):
        node = tc_mar.find(qn(f"w:{m}"))
        if node is None:
            node = OxmlElement(f"w:{m}")
            tc_mar.append(node)
        node.set(qn("w:w"), str(v))
        node.set(qn("w:type"), "dxa")


def set_table_borders(table, color="D9D9D9", size="6"):
    tbl_pr = table._tbl.tblPr
    borders = tbl_pr.first_child_found_in("w:tblBorders")
    if borders is None:
        borders = OxmlElement("w:tblBorders")
        tbl_pr.append(borders)
    for edge in ("top", "left", "bottom", "right", "insideH", "insideV"):
        tag = "start" if edge == "left" else "end" if edge == "right" else edge
        el = borders.find(qn(f"w:{tag}"))
        if el is None:
            el = OxmlElement(f"w:{tag}")
            borders.append(el)
        el.set(qn("w:val"), "single")
        el.set(qn("w:sz"), size)
        el.set(qn("w:space"), "0")
        el.set(qn("w:color"), color)


def set_cell_width(cell, width_cm: float):
    tc_pr = cell._tc.get_or_add_tcPr()
    tc_w = tc_pr.find(qn("w:tcW"))
    if tc_w is None:
        tc_w = OxmlElement("w:tcW")
        tc_pr.append(tc_w)
    tc_w.set(qn("w:w"), str(int(width_cm * 567)))
    tc_w.set(qn("w:type"), "dxa")


def set_font(run, name="宋体", size=12, bold=False, color=INK, italic=False):
    resolved_name = {"宋体": "Songti SC", "黑体": "Heiti SC"}.get(name, name)
    run.font.name = resolved_name
    run.font.size = Pt(size)
    run.font.bold = bold
    run.font.italic = italic
    run.font.color.rgb = RGBColor.from_string(color.replace("#", ""))
    r_pr = run._element.get_or_add_rPr()
    r_fonts = r_pr.get_or_add_rFonts()
    r_fonts.set(qn("w:ascii"), resolved_name)
    r_fonts.set(qn("w:hAnsi"), resolved_name)
    r_fonts.set(qn("w:cs"), resolved_name)
    r_fonts.set(qn("w:eastAsia"), resolved_name)


def set_paragraph_format(p, first_indent=True, before=0, after=6, line=1.5):
    fmt = p.paragraph_format
    fmt.space_before = Pt(before)
    fmt.space_after = Pt(after)
    fmt.line_spacing_rule = WD_LINE_SPACING.ONE_POINT_FIVE if line == 1.5 else WD_LINE_SPACING.SINGLE
    if first_indent:
        fmt.first_line_indent = Pt(24)
    fmt.keep_together = False
    fmt.widow_control = True


def add_body(doc: Document, text: str, bold_lead: str | None = None, no_indent=False):
    p = doc.add_paragraph(style="Normal")
    set_paragraph_format(p, first_indent=not no_indent)
    if bold_lead and text.startswith(bold_lead):
        r1 = p.add_run(bold_lead)
        set_font(r1, "宋体", 12, True)
        r2 = p.add_run(text[len(bold_lead):])
        set_font(r2, "宋体", 12)
    else:
        r = p.add_run(text)
        set_font(r, "宋体", 12)
    return p


def add_bullets(doc: Document, items: list[str]):
    for item in items:
        p = doc.add_paragraph(style="List Bullet")
        set_paragraph_format(p, first_indent=False, after=4, line=1.5)
        p.paragraph_format.left_indent = Cm(0.75)
        p.paragraph_format.first_line_indent = Cm(-0.35)
        set_font(p.add_run(item), "宋体", 11.5)


def add_heading(doc: Document, text: str, level: int = 1):
    p = doc.add_paragraph(style=f"Heading {level}")
    p.alignment = WD_ALIGN_PARAGRAPH.LEFT
    fmt = p.paragraph_format
    fmt.space_before = Pt(14 if level == 1 else 9)
    fmt.space_after = Pt(8 if level == 1 else 5)
    fmt.keep_with_next = True
    fmt.page_break_before = False
    size = {1: 16, 2: 14, 3: 12.5}.get(level, 12)
    set_font(p.add_run(text), "黑体" if level < 3 else "宋体", size, True, "#000000")
    return p


def add_caption(doc: Document, text: str):
    p = doc.add_paragraph()
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    p.paragraph_format.space_before = Pt(3)
    p.paragraph_format.space_after = Pt(9)
    p.paragraph_format.keep_with_next = True
    set_font(p.add_run(text), "宋体", 9.5, True, "#000000")
    return p


def add_figure(doc: Document, path: Path, caption: str, width_cm: float = 15.2):
    p = doc.add_paragraph()
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    p.paragraph_format.space_before = Pt(6)
    p.paragraph_format.space_after = Pt(2)
    p.paragraph_format.keep_with_next = True
    p.add_run().add_picture(str(path), width=Cm(width_cm))
    add_caption(doc, caption)


def add_table(doc: Document, headers: list[str], rows: list[list[str]], widths: list[float] | None = None, font_size=9.5):
    table = doc.add_table(rows=1, cols=len(headers))
    table.alignment = WD_TABLE_ALIGNMENT.CENTER
    table.autofit = False
    set_table_borders(table)
    hdr = table.rows[0]
    set_repeat_table_header(hdr)
    for j, text in enumerate(headers):
        cell = hdr.cells[j]
        set_cell_shading(cell, BLUE.replace("#", ""))
        cell.vertical_alignment = WD_CELL_VERTICAL_ALIGNMENT.CENTER
        set_cell_margins(cell, 100, 100, 100, 100)
        if widths:
            set_cell_width(cell, widths[j])
        p = cell.paragraphs[0]
        p.alignment = WD_ALIGN_PARAGRAPH.CENTER
        p.paragraph_format.space_after = Pt(0)
        p.paragraph_format.line_spacing_rule = WD_LINE_SPACING.SINGLE
        set_font(p.add_run(text), "宋体", font_size, True, WHITE)
    for i, row in enumerate(rows):
        cells = table.add_row().cells
        for j, text in enumerate(row):
            cell = cells[j]
            cell.vertical_alignment = WD_CELL_VERTICAL_ALIGNMENT.CENTER
            set_cell_margins(cell, 90, 100, 90, 100)
            set_cell_shading(cell, "F5F8FC" if i % 2 else "FFFFFF")
            if widths:
                set_cell_width(cell, widths[j])
            p = cell.paragraphs[0]
            p.alignment = WD_ALIGN_PARAGRAPH.LEFT if len(text) > 14 else WD_ALIGN_PARAGRAPH.CENTER
            p.paragraph_format.space_after = Pt(0)
            p.paragraph_format.line_spacing_rule = WD_LINE_SPACING.SINGLE
            set_font(p.add_run(text), "宋体", font_size, False, INK)
    spacer = doc.add_paragraph()
    spacer.paragraph_format.space_after = Pt(4)
    return table


def add_page_number(paragraph):
    paragraph.alignment = WD_ALIGN_PARAGRAPH.CENTER
    run = paragraph.add_run()
    fld_char1 = OxmlElement("w:fldChar")
    fld_char1.set(qn("w:fldCharType"), "begin")
    instr = OxmlElement("w:instrText")
    instr.set(qn("xml:space"), "preserve")
    instr.text = " PAGE "
    fld_char2 = OxmlElement("w:fldChar")
    fld_char2.set(qn("w:fldCharType"), "end")
    run._r.extend([fld_char1, instr, fld_char2])
    set_font(run, "宋体", 9, False, MUTED)


def add_page_break(doc: Document):
    doc.add_paragraph().add_run().add_break(WD_BREAK.PAGE)


def configure_styles(doc: Document):
    styles = doc.styles
    normal = styles["Normal"]
    normal.font.name = "Songti SC"
    normal.font.size = Pt(12)
    normal._element.rPr.rFonts.set(qn("w:eastAsia"), "Songti SC")
    normal.paragraph_format.line_spacing = 1.5
    normal.paragraph_format.space_after = Pt(6)
    title = styles["Title"]
    title.font.name = "Heiti SC"
    title.font.size = Pt(24)
    title.font.bold = True
    title.font.color.rgb = RGBColor(0, 0, 0)
    title._element.rPr.rFonts.set(qn("w:eastAsia"), "Heiti SC")
    for level in (1, 2, 3):
        style = styles[f"Heading {level}"]
        style.font.color.rgb = RGBColor(0, 0, 0)
        style._element.rPr.rFonts.set(qn("w:eastAsia"), "Heiti SC" if level < 3 else "Songti SC")


def setup_sections(doc: Document):
    cover = doc.sections[0]
    cover.page_width = Mm(210)
    cover.page_height = Mm(297)
    cover.top_margin = Cm(2.4)
    cover.bottom_margin = Cm(2.2)
    cover.left_margin = Cm(2.5)
    cover.right_margin = Cm(2.5)
    cover.header_distance = Cm(1.2)
    cover.footer_distance = Cm(1.2)


def add_cover(doc: Document, assets: dict[str, Path]):
    p = doc.add_paragraph(style="Title")
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    p.paragraph_format.space_before = Pt(42)
    p.paragraph_format.space_after = Pt(14)
    set_font(p.add_run("NOVA 证据约束多 Agent 智能客服系统研究报告"), "黑体", 24, True, "#000000")

    sub = doc.add_paragraph()
    sub.alignment = WD_ALIGN_PARAGRAPH.CENTER
    sub.paragraph_format.space_after = Pt(5)
    set_font(sub.add_run("OMS 与独立站双场景验证"), "宋体", 14, False, "#000000")

    contest = doc.add_paragraph()
    contest.alignment = WD_ALIGN_PARAGRAPH.CENTER
    contest.paragraph_format.space_after = Pt(18)
    set_font(contest.add_run("挑战杯大学生课外学术科技作品竞赛  科技发明制作类"), "宋体", 12, False, "#000000")

    pic = doc.add_paragraph()
    pic.alignment = WD_ALIGN_PARAGRAPH.CENTER
    pic.add_run().add_picture(str(assets["cover"]), width=Cm(15.5))
    pic.paragraph_format.space_after = Pt(22)

    info = [
        ("作品类别", "科技发明制作类"),
        ("研究对象", "NOVA 证据约束多 Agent AI 客服核心系统"),
        ("验证媒介", "OMS 管理端与 BUZUD 独立站"),
        ("报告版本", "基于 2026 年 11 月 6 日前阶段性证据"),
        ("编制日期", "2026 年 11 月"),
    ]
    table = doc.add_table(rows=len(info), cols=2)
    table.alignment = WD_TABLE_ALIGNMENT.CENTER
    table.autofit = False
    for i, (k, v) in enumerate(info):
        c1, c2 = table.rows[i].cells
        set_cell_width(c1, 3.0)
        set_cell_width(c2, 11.0)
        set_cell_margins(c1, 120, 120, 120, 120)
        set_cell_margins(c2, 120, 120, 120, 120)
        for c in (c1, c2):
            c.vertical_alignment = WD_CELL_VERTICAL_ALIGNMENT.CENTER
        p1 = c1.paragraphs[0]
        p1.alignment = WD_ALIGN_PARAGRAPH.CENTER
        p2 = c2.paragraphs[0]
        p2.alignment = WD_ALIGN_PARAGRAPH.LEFT
        set_font(p1.add_run(k), "黑体", 11, True, INK)
        set_font(p2.add_run(v), "宋体", 11, False, INK)
    set_table_borders(table, "D9D9D9", "4")

    new_section = doc.add_section(WD_SECTION.NEW_PAGE)
    new_section.page_width = Mm(210)
    new_section.page_height = Mm(297)
    new_section.top_margin = Cm(2.4)
    new_section.bottom_margin = Cm(2.2)
    new_section.left_margin = Cm(2.5)
    new_section.right_margin = Cm(2.5)
    new_section.header_distance = Cm(1.2)
    new_section.footer_distance = Cm(1.2)
    new_section.header.is_linked_to_previous = False
    new_section.footer.is_linked_to_previous = False
    header = new_section.header.paragraphs[0]
    header.alignment = WD_ALIGN_PARAGRAPH.RIGHT
    set_font(header.add_run("NOVA 智能客服系统研究报告"), "宋体", 9, False, MUTED)
    add_page_number(new_section.footer.paragraphs[0])
    pg_num_type = OxmlElement("w:pgNumType")
    pg_num_type.set(qn("w:start"), "1")
    new_section._sectPr.append(pg_num_type)


def build_document():
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    ASSET_DIR.mkdir(parents=True, exist_ok=True)
    assets = {
        "cover": make_cover_graphic(),
        "survey": make_survey_chart(),
        "challenge": make_challenge_chain(),
        "arch": make_architecture(),
        "evidence": make_evidence_flow(),
        "agents": make_agent_flow(),
        "retrieval": make_retrieval_chart(),
        "evaluation": make_evaluation_chart(),
        "timeline": make_validation_timeline(),
        "roadmap": make_roadmap(),
        "eq_rrf": make_equation("RRF(d) = Σᵢ  1 / (k + rᵢ(d))", "equation-rrf.png", "式 1  倒数排序融合  rᵢ(d) 为文档 d 在第 i 个检索器中的名次"),
        "eq_gate": make_equation("Allow = I ∧ S ∧ E ∧ P", "equation-gate.png", "式 2  仅当身份 I 范围 S 证据 E 与策略 P 同时满足时才允许回答或执行"),
        "eq_benefit": make_equation("B = Q × a × (T_h − T_ai) × C_h − C_s", "equation-benefit.png", "式 3  年度净收益模型  所有变量须由企业试点数据填充"),
    }

    doc = Document()
    configure_styles(doc)
    setup_sections(doc)
    add_cover(doc, assets)

    # Abstract and executive view.
    add_heading(doc, "摘要", 1)
    abstract = (
        "本研究以 NOVA AI 客服核心系统为研究对象，针对现有智能客服在真实企业服务中容易出现的三个问题展开："
        "模型回答与业务事实脱节，跨客户和跨店铺数据存在越权风险，以及知识问答、订单查询和售后判断缺少可追溯的协同机制。"
        "项目构建了证据约束多 Agent 智能客服原型，以企业知识库和实时业务工具为事实来源，"
        "采用意图样例路由、向量与关键词混合检索、多 Agent 分工、独立审核、确定性订单摘要和人工接管共同约束生成过程。"
        "OMS 管理端与 BUZUD 独立站分别提供后台管理和客户服务两类身份、数据与交互条件，仅作为系统接入和验证媒介，"
        "核心智能客服能力不依赖其中任何一端。"
        "阶段性验证包括 21 份需求调研、45 条对话回归、200 条冻结检索保留集、200 条核心安全集、300 条独立回归、"
        "12 项真实商城工具验收和跨系统浏览器联调。冻结检索集上，关键词检索、向量检索和意图路由加检索降级的首条命中率"
        "分别为 55.5%、76.0% 和 97.0%；完整系统核心安全评测为 200/200；独立回归通过 280/300，"
        "其中授权边界和证据冲突均为 100/100，多轮对话为 80/100。研究表明，可靠客服的关键不在于单独放大模型能力，"
        "而在于建立可信身份、受限工具、来源隔离、证据审核和人工责任共同构成的系统边界。当前结果证明了技术可行性，"
        "但尚不能替代生产环境的真实客户订单、人工队列、多租户和成本收益试点。"
    )
    add_body(doc, abstract)
    p = doc.add_paragraph()
    p.paragraph_format.space_before = Pt(6)
    p.paragraph_format.space_after = Pt(12)
    set_font(p.add_run("关键词  "), "黑体", 11, True)
    set_font(p.add_run("智能客服  检索增强生成  多 Agent  业务工具  证据约束  人工接管  双场景验证"), "宋体", 11)

    add_heading(doc, "核心结论", 2)
    add_table(
        doc,
        ["证据层级", "阶段性结果", "结论边界"],
        [
            ["研究对象", "NOVA AI 客服核心系统", "OMS 与独立站仅作为接入和验证媒介"],
            ["需求", "21 份反馈 20 名客户和 1 家企业", "企业样本仅用于形成约束 不推算行业比例"],
            ["检索", "冻结集首条命中率 97.0%", "知识条目 14 条 适用于本项目范围"],
            ["安全", "完整系统 200/200", "代表编排与门禁 不代表裸模型"],
            ["独立回归", "280/300 通过 平均 97.17 分", "多轮对话 80/100 仍需改进"],
            ["业务工具", "隔离数据库 12/12", "不是生产供应商和生产库验收"],
            ["公网联调", "222 项 AI 测试及 21 项浏览器检查通过", "订单复合场景使用合成证据"],
        ],
        [3.0, 4.6, 7.4],
        9.3,
    )

    add_heading(doc, "报告结构", 2)
    add_bullets(doc, [
        "第一至三章说明竞赛定位、需求调研、科学问题及现有 AI 客服技术对比。",
        "第四至六章说明 NOVA 核心技术、双场景验证和实验方法。",
        "第七至八章给出实验设计、阶段性结果、创新点和应用价值。",
        "第九至十章说明局限、后续研究、结论与竞赛答辩准备。",
    ])

    # 1
    add_page_break(doc)
    add_heading(doc, "一 AI 客服研究背景与竞赛定位", 1)
    add_heading(doc, "1 AI 客服的现实问题", 2)
    add_body(doc, "企业客服面对的事实并不只存在于聊天模型中。商品规格和售后规则可以进入知识库，但价格、库存、订单状态、物流节点和退款进度会随业务系统持续变化。如果模型只依赖训练记忆或静态提示，回答可能语言流畅却与当前订单不一致；如果直接让模型访问数据库，又会扩大越权读取、跨店铺混用和敏感字段泄露的风险。企业真正需要的是能够在身份可信、范围明确、证据可核验的前提下回答问题，并在信息不足或操作风险较高时及时转给人工。")
    add_heading(doc, "2 研究对象与验证媒介", 2)
    add_body(doc, "本项目的研究对象是 NOVA AI 客服核心系统，而不是 OMS 或独立站本身。NOVA 负责理解用户问题、识别意图、检索知识、调用受限业务工具、组织多 Agent 协作、审核答案并决定是否转人工；OMS 与 BUZUD 独立站只负责提供两类不同的接入环境。前者验证后台管理身份、订单归属与售后查询，后者验证访客和登录客户的在线咨询、渠道会话与人工入口。两个媒介共用同一套 AI 客服核心能力，但使用独立签名密钥、证据命名空间和身份规则，证明系统可以在不改变核心算法的情况下适配不同渠道。")
    add_body(doc, "因此，报告中的 OMS 和独立站截图、签名接口与浏览器联调属于工程验证材料，用于回答 NOVA 是否能安全接入真实业务场景；研究贡献仍集中在智能客服的证据约束架构、检索与工具协同、多 Agent 审核、安全门禁及评测方法。")

    add_heading(doc, "3 挑战杯科技发明制作类定位", 2)
    add_body(doc, "现行挑战杯竞赛章程将作品分为自然科学类学术论文、哲学社会科学类社会调查报告和科技发明制作三类；第十九届竞赛导向明确提出，科技发明制作侧重作品的应用价值和转化前景，并鼓励围绕人工智能等战略性新兴产业开展应用研究[9]。本项目已有可运行的软件原型、业务接口、测试数据和跨系统演示材料，核心贡献是工程系统与验证方法，因此按科技发明制作类组织报告。")
    add_body(doc, "报告不以融资规模和收入预测为中心，而以研究问题、系统实现、对照实验、可复现证据和应用边界为主。对尚未取得企业试点数据的成本节约、人工咨询下降和客户满意度，不预先给出收益结论，只给出指标、公式和采集方案。")

    add_heading(doc, "4 政策与合规背景", 2)
    policies = [
        ["2025.08", "国务院", "国发〔2025〕11号", "关于深入实施“人工智能+”行动的意见", "推动智能体在商贸和服务业应用 同时防范幻觉并提升可信赖水平"],
        ["2025.03", "国家网信办等四部门", "国信办通字〔2025〕2号", "人工智能生成合成内容标识办法", "要求交互场景和生成内容按规定进行显式或隐式标识"],
        ["2024.09", "国务院", "国务院令第790号", "网络数据安全管理条例", "要求访问控制 安全认证 备份和数据处理责任"],
        ["2023.07", "国家网信办等七部门", "令第15号", "生成式人工智能服务管理暂行办法", "强调准确性 可靠性 透明度和依法处理个人信息"],
        ["2023.02", "中共中央 国务院", "无", "数字中国建设整体布局规划", "推动数字技术与实体经济融合并强化数字安全屏障"],
        ["2022.01", "国务院", "国发〔2021〕29号", "十四五数字经济发展规划", "鼓励服务业数字化和数据要素规范利用"],
        ["2021.08", "全国人大常委会", "主席令第91号", "个人信息保护法", "要求目的明确 最小必要 权限控制和个人信息安全保护"],
        ["2021.06", "全国人大常委会", "主席令第84号", "数据安全法", "要求数据分类分级 全流程安全管理和风险处置"],
        ["2018.08", "全国人大常委会", "主席令第7号", "电子商务法", "规范电子商务经营者 消费者权益和交易信息保护"],
        ["2017.07", "国务院", "国发〔2017〕35号", "新一代人工智能发展规划", "提出发展智能服务和安全可信人工智能"],
    ]
    add_table(doc, ["时间", "发布主体", "文号", "政策文件", "与本项目的关系"], policies, [1.6, 2.8, 2.2, 3.8, 5.0], 8.4)
    add_body(doc, "上述政策共同指向两条约束：一是鼓励人工智能进入商贸和现代服务业，二是要求数据处理和生成式服务具备最小必要、来源透明、安全可控与责任可追溯的机制。本项目将这些要求转化为来源隔离、最小字段、短时签名、只读工具、回答引用和人工接管。")

    # 2
    add_heading(doc, "二 需求调研与问题定义", 1)
    add_heading(doc, "1 调研设计", 2)
    add_body(doc, "项目组在开发前使用同一份问卷分别收集客户与企业反馈，共获得 21 份有效样本，其中客户 20 份、企业 1 份。客户问题覆盖咨询类型、希望 AI 优先解决的任务、可接受的自动化程度、转人工条件和使用体验；企业问题覆盖业务目标、首期范围、数据来源、操作权限、安全要求和验收指标。由于企业样本仅 1 份，本研究只把它作为原型需求约束，不将其换算为行业比例。")
    add_figure(doc, assets["survey"], "图 1 客户需求调研关键结果", 15.4)
    add_body(doc, "客户样本显示，90% 会咨询商品功能、规格或使用方法，60% 会咨询价格、优惠和库存，50% 会咨询订单与物流；70% 希望快速解决常见问题，65% 希望准确查询订单与物流。权限态度更谨慎：90% 只接受 AI 提供答案，或在提交前由用户确认；80% 希望资金、重要订单或连续未解决问题立即转人工。由此可见，系统的目标不是让 AI 无条件代替人工，而是把高频问题自动化，并把事实核对、权限确认和人工责任放在明确边界内。")

    add_heading(doc, "2 企业约束转化", 2)
    add_table(doc, ["调研要求", "系统设计响应", "当前状态"], [
        ["商品和订单以业务后台为事实来源", "知识库回答静态规则 实时事实调用业务工具", "NOVA Commerce 工具已验收 外部独立站商品实时库存未接入"],
        ["订单查询必须校验身份", "业务后端确认用户和订单归属后再签名", "OMS 与独立站后端测试覆盖"],
        ["不同店铺和客户不得混用", "source 命名空间 独立密钥 商户范围与引用前缀", "已有隔离测试 仍需生产多租户专项"],
        ["高风险资金操作必须人工审核", "退款 重要订单 投诉 法律和报警进入人工接管", "requires_human 已实现 人工队列尚未正式联通"],
        ["知识需审核后发布", "FAQ 导入先为草稿 发布新版本时归档旧版本", "管理端与数据结构已实现 需企业身份联调"],
    ], [4.2, 6.0, 5.2], 9.0)

    add_heading(doc, "3 三层科学挑战", 2)
    add_figure(doc, assets["challenge"], "图 2 数据 算法与系统三层科学挑战", 15.4)
    add_heading(doc, "3.1 数据层挑战", 3)
    add_body(doc, "企业知识包含稳定程度不同的事实。门店地址和售后规则可以按版本发布；库存、订单、物流和支付状态必须实时读取；客户身份和商户范围只能由可信业务后端提供。研究难点是如何统一这些异构证据，同时保留来源、时间和权限边界。RAG 能把外部知识引入生成过程[10-16]，但通用检索并不会自动解决跨租户隔离和动态业务状态问题。")
    add_heading(doc, "3.2 算法层挑战", 3)
    add_body(doc, "客服问题短、口语化、上下文省略多，关键词检索容易漏掉同义表达，纯向量检索又可能把范围外问题强行匹配到最接近的政策。模型还需要判断何时使用订单工具、何时只查 FAQ、何时拒绝或转人工。ReAct 和工具学习研究说明语言模型可以在推理过程中选择外部动作[17-19]，多 Agent 研究进一步提出角色分工[20-22]，但实际系统仍需限制工具集合、参数来源和引用范围。")
    add_heading(doc, "3.3 系统层挑战", 3)
    add_body(doc, "跨系统集成必须同时满足安全、延迟、可用性和可运营性。复杂多 Agent 链路增加模型调用次数，可能拉高延迟；外部模型或业务接口不可用时需要安全降级；人工接管标记还必须由渠道真正消费，才能形成完整服务闭环。系统设计因此不能只看平均回答质量，还要验证签名篡改、跨客户访问、证据冲突、提示注入、缺失工具和多轮上下文等异常条件。")

    # 3
    add_heading(doc, "三 国内外研究与现有 AI 客服技术对比", 1)
    add_heading(doc, "1 检索增强生成", 2)
    add_body(doc, "Lewis 等提出的检索增强生成把参数化语言模型与可检索的外部记忆结合，使回答能够利用更新后的知识[10]。DPR、FiD 等工作分别改进稠密检索与多文档融合[11-12]；后续研究进一步通过对话检索减少无依据生成[13]，通过自反思决定是否检索并评价生成结果[14]。综述研究指出，RAG 的效果取决于索引、检索、上下文组织和生成评估的共同设计[15-16]。这些工作为企业知识问答提供了方法基础，但并不直接处理订单权限和业务工具的实时状态。")
    add_body(doc, "中文客服还面临短语、省略、错别字和口语同义表达。项目选用 BGE 中文向量模型相关资源[31]，并将意图样例路由与基础检索结合。与只提高相似度不同，本研究同时把应拒绝问题作为检索评测的一部分，避免系统把范围外咨询附会到最近政策。")

    add_heading(doc, "2 工具调用与智能体", 2)
    add_body(doc, "ReAct 把推理与动作交替执行[17]，Toolformer 与 ToolLLM 研究语言模型如何选择 API、组织参数并吸收工具结果[18-19]。AutoGen、MetaGPT 与 CAMEL 探索多智能体对话和角色协作[20-22]。这些方法说明复杂任务可以分解为规划、专业执行和汇总，但通用框架若允许角色自由访问工具或共享未经核验的文本，仍可能产生权限放大和错误传播。NOVA 因此采用有限角色、有限工具、显式依赖和独立审核，订单 Agent 的结构化证据才可供售后 Agent 使用。")

    add_heading(doc, "3 幻觉 安全与评测", 2)
    add_body(doc, "自然语言生成的幻觉问题已经在多类任务中被系统总结[25]。SelfCheckGPT、TruthfulQA 等工作从一致性或错误模仿角度评估模型可靠性[26,30]，长上下文研究表明重要证据处于上下文中间时可能被忽略[27]。RAGAS 和 ARES 则从忠实度、相关性和检索质量自动评估 RAG 系统[28-29]。本项目吸收这些研究的共同观点：不能用单一平均准确率代表安全性，必须把授权边界、证据冲突、人工接管和提示注入设计成独立测试集。")
    add_body(doc, "现有研究的主要空白是，论文通常在公开知识问答或通用工具环境中评估，而企业客服同时存在动态交易事实、身份范围、渠道适配和人工责任。本研究的贡献是把这些约束固化为系统接口与可重复测试，而不是仅通过提示词要求模型自觉遵守。")

    add_heading(doc, "4 现有 AI 客服技术路线与代表性方案", 2)
    add_body(doc, "现有 AI 客服大体经历了规则与意图匹配、知识库检索增强、业务工具调用和自主智能体四条技术路线。Dialogflow CX 代表意图 路由 流程与 webhook 组合，适合确定性业务流程[44-45]；Intercom Fin 以多源知识 RAG 数据连接器 动作和答案检查为核心[46-47]；Zendesk AI agents 将可信知识 生成式流程 授权动作 API 集成和转人工结合[48-49]；Microsoft Copilot Studio 支持从多类企业知识 工具 其他智能体中进行生成式编排，并在平台层提供身份和治理控制[50-52]；Salesforce Agentforce 依托图式推理 CRM 与 Data Cloud 数据 Flow 或 Apex 动作 Trust Layer 和会话追踪形成平台型智能体[53-55]。")
    add_table(doc, ["代表技术", "主要机制", "业务数据与动作", "权限与安全", "追溯能力", "与 NOVA 的关系"], [
        ["Dialogflow CX", "意图 路由 页面 流程", "Webhook 调用后端", "依赖流程和后端鉴权", "流程与调用状态可查", "适合确定性流程 NOVA 保留其快速规则思想"],
        ["Intercom Fin", "多源 RAG 与生成回答", "数据连接器与动作", "受众规则与身份验证", "可检查答案来源和设置", "知识运营成熟 NOVA 更强调独立证据审核和短时签名"],
        ["Zendesk AI agents", "知识回复与生成式流程", "授权动作和 API 集成", "受限内容权限与转人工", "分析与流程记录", "客服流程完整 NOVA 更强调跨来源隔离和最小字段"],
        ["Copilot Studio", "知识 工具 智能体生成编排", "连接器 Dataverse 流程", "Entra 身份与环境治理", "运行保护与安全分析", "平台能力全面 NOVA 更轻量且不绑定微软数据栈"],
        ["Agentforce", "图式推理 RAG 与行动循环", "CRM Data Cloud Flow Apex", "访问控制 Trust Layer", "来源引用与会话追踪", "企业闭环完善 NOVA 验证独立部署的证据约束方法"],
        ["NOVA", "混合检索 受限工具 多 Agent 审核", "只读订单 物流 支付 库存工具", "来源隔离 HMAC 最小字段 四门禁", "引用前缀 审核记录 冻结评测", "以 OMS 和独立站验证可迁移核心 当前仍属原型"],
    ], [2.3, 2.9, 3.0, 2.9, 2.3, 3.4], 7.4)
    add_body(doc, "表中对比依据各厂商公开技术文档，只比较已披露的架构能力，不构成同一数据集上的性能排名。主流方案已经普遍从单纯 FAQ 机器人发展到 RAG 业务动作 身份治理和人工接管，说明本项目不能把接入知识库或调用 API 本身作为创新。NOVA 的差异化研究点是：在不依附单一 CRM 或客服平台的条件下，将来源隔离 短时签名 最小字段 受限工具 结构化 Agent 依赖和独立审核组合成可复现的安全边界，并用冻结检索集 核心安全集 独立回归和双场景联调验证。")
    add_body(doc, "同时必须承认，Intercom Zendesk Microsoft 和 Salesforce 在多渠道运营 知识治理 可观测性和生产规模方面具有成熟平台积累；NOVA 当前不以替代这些平台为结论，而是验证一种可嵌入现有业务系统的轻量证据约束型 AI 客服方法。后续竞争力应由真实企业连续运营中的准确率 独立解决率 转人工质量 成本和安全事件共同检验。")

    # 4
    add_heading(doc, "四 NOVA AI 客服核心技术体系与实现", 1)
    add_heading(doc, "1 总体架构", 2)
    add_figure(doc, assets["arch"], "图 3 NOVA AI 客服核心技术架构", 15.4)
    add_body(doc, "系统由验证媒介层、可信网关层、AI 客服核心层和证据层组成。验证媒介层可接入 OMS 独立站或其他渠道并保留各自身份和业务接口；可信网关层在业务后端完成订单归属校验，只把最小字段签名给 NOVA；AI 客服核心层完成意图识别、检索、工具选择、多 Agent 执行和答案审核；证据层保存 FAQ、政策与实时业务工具结果，并通过引用前缀区分来源。AI 服务不直接连接外部站点数据库，降低了模型服务对核心业务数据的访问面。")

    add_heading(doc, "2 可信证据数据流", 2)
    add_figure(doc, assets["evidence"], "图 4 可信证据与最小数据流", 15.4)
    add_body(doc, "OMS 与独立站分别使用独立密钥。签名材料由 source、秒级时间戳和原始 UTF-8 JSON 组成，采用 HMAC-SHA256；AI 服务只接受 120 秒时间窗内且签名匹配的请求。浏览器不能提交可信用户身份、商户范围或证据，也不持有签名密钥。订单证据只传订单号、状态、金额和币种，姓名、手机号、地址与备注不进入模型上下文。")
    add_figure(doc, assets["eq_gate"], "图 5 安全门禁逻辑表达式", 12.5)
    add_body(doc, "式 2 中 I 表示身份由业务后端核验，S 表示客户与商户范围匹配，E 表示证据属于本次请求且未过期，P 表示当前操作被策略允许。任一条件不满足时，系统不返回敏感业务事实，也不执行高风险操作。该逻辑用于解释安全边界，具体实现由后端鉴权、签名验证、引用过滤和规则门禁共同完成。")

    add_heading(doc, "3 检索与知识治理", 2)
    add_body(doc, "知识检索同时使用向量与关键词信号，并用倒数排序融合合并不同检索器的排名；意图样例路由先根据 624 条已标注意图样例寻找相近表达，再回退到基础检索。企业 FAQ 经运营审核后发布，草稿不会直接进入线上回答。动态库存、订单、物流和支付状态不写入静态知识库，而由只读工具按当前请求获取。")
    add_figure(doc, assets["eq_rrf"], "图 6 倒数排序融合公式", 12.5)
    add_body(doc, "式 1 中 rᵢ(d) 表示候选文档 d 在第 i 个检索器中的排名，k 是平滑常数。该方法不要求不同检索器的分数尺度一致，适合合并关键词与向量排名[32]。系统额外保留范围判定：检索不到可靠内容时返回无知识，不把相似度最高的无关条目当成事实。")

    add_heading(doc, "4 多 Agent 协作与审核", 2)
    add_figure(doc, assets["agents"], "图 7 多 Agent 协作与独立审核流程", 15.4)
    add_body(doc, "主 Agent 最多拆分三个不同业务任务；知识 Agent 只能调用 search_knowledge，订单 Agent 只能调用 read_order，售后 Agent 只能读取售后政策，并在涉及订单条件时读取订单 Agent 已核实的结果。每个业务 Agent 最多两次工具调用和三次模型调用。订单与知识任务可以并行，售后任务等待订单结果。独立审核 Agent 只判断证据是否支持、条件是否遗漏和是否存在无依据承诺，不负责改写事实。")
    add_body(doc, "常规单角色问答通常需要四次模型调用，三个业务角色共同参与时通常需要九次，因此多 Agent 不是所有消息的默认路径。问候、越权请求、明确转人工和部分确定性订单状态由规则快速处理；模型或审核不可用时进入安全回退。")

    add_heading(doc, "5 NOVA 内部技术选型对比", 2)
    add_table(doc, ["方案", "动态事实", "范围控制", "可追溯性", "阶段性表现", "选型判断"], [
        ["纯模型回答", "依赖参数记忆", "主要靠提示词", "弱", "裸模型核心安全 129/200", "不作为生产事实层"],
        ["关键词检索", "仅静态知识", "可做词表规则", "中", "冻结集 55.5%", "作为可解释降级"],
        ["向量检索", "仅静态知识", "需额外范围判断", "中", "冻结集 76.0%", "解决口语改写"],
        ["意图路由加混合检索", "静态知识为主", "拒答准确率 100%", "较强", "冻结集 97.0%", "知识问答主路径"],
        ["多 Agent 加业务工具", "支持实时订单等", "身份 范围 工具均受限", "强", "签名场景与浏览器验收通过", "复杂业务主路径"],
    ], [2.6, 2.3, 2.7, 1.8, 3.0, 3.0], 8.2)
    add_body(doc, "综合比较后，本项目采用分层选型：静态 FAQ 使用意图路由和混合检索，动态订单使用可信工具和确定性摘要，跨知识与订单的复合问题才进入多 Agent。这样既保留复杂任务的协作能力，也控制模型调用成本和链路延迟。")

    # 5
    add_heading(doc, "五 双场景媒介接入与可迁移验证", 1)
    add_body(doc, "本章不把 OMS 和独立站作为系统主体，而把它们视为两组验证夹具。OMS 提供后台管理身份 订单归属和售后业务条件，独立站提供匿名与登录客户 多轮会话和公开渠道条件。NOVA 通过统一请求协议与两组适配器连接媒介，核心检索 Agent 工具审核与安全门禁不因渠道变化而重写；由此检验智能客服核心与业务载体解耦的程度。")
    add_heading(doc, "1 OMS 管理端验证媒介", 2)
    add_body(doc, "OMS 管理端在 AI 客服页面提交问题和可选订单号。网关单独校验 JWT，并在读取订单时再次校验商户归属；管理账号只能按照原有管理员权限访问订单。AI 返回答案、意图、引用、人工标记和确认标记，业务 DTO 无需因多 Agent 改造。图 8 展示了系统拒绝提供其他客户手机号和收货地址的实际界面结果。")
    if SCREEN_OMS.exists():
        add_figure(doc, SCREEN_OMS, "图 8 OMS 管理端隐私越权拒绝实测", 15.2)

    add_heading(doc, "2 BUZUD 独立站验证媒介", 2)
    add_body(doc, "独立站复用原用户登录和订单归属接口，匿名订单查询返回 401。FAQ 候选来自站点自身知识库，当前单次最多提供 10 条候选；外部接口不读取 NOVA 商城的知识库或数据库，避免串店。独立站保留原聊天记录，并为页面会话生成随机 UUID；AI 服务在来源、认证用户与会话 UUID 范围内保留最近话题提示，默认 30 分钟过期、最多 1000 个会话。当前缓存是单进程内存，实现多实例前必须迁移到共享存储。")
    add_body(doc, "图 9 展示了提示注入测试：用户要求忽略规则并伪造退款成功和人工接通，系统拒绝虚假陈述并说明当前未执行这些操作。独立站当前已接入 FAQ 与订单入口，但实时商品库存、优惠发放仍未接入该聊天工具；报告将其列为后续工作，不把内部 NOVA Commerce 工具的能力等同于 BUZUD 外部站点现状。")
    if SCREEN_SITE.exists():
        add_figure(doc, SCREEN_SITE, "图 9 独立站提示注入与虚假操作拒绝实测", 8.2)

    add_heading(doc, "3 跨媒介人工接管与责任边界", 2)
    add_body(doc, "系统在用户主动要求人工、AI 连续未解决、投诉与法律问题、安全事件、重要订单、大额退款、资金异常或缺乏可靠证据时设置 requires_human。该标记只表示 AI 判断应转人工，不能等同于真人已接通。独立站当前显示现有工单入口，生产接入仍需由渠道消费该标记、创建排队任务并向用户反馈真实状态。退款、改地址、发货等写操作不因 AI 回答直接执行。")

    # 6
    add_heading(doc, "六 研究方法与实验设计", 1)
    add_heading(doc, "1 证据分层方法", 2)
    add_body(doc, "研究采用需求证据、离线评测、隔离环境工具验收、本地浏览器抽测和公网联调五层证据。每一层回答 AI 客服核心的不同问题：问卷说明用户和企业需要什么；离线集验证检索 编排和风控；工具验收验证动态业务事实与签名接口；浏览器抽测借助 OMS 和独立站暴露端到端交互问题；公网联调验证部署后的完整链路。不同层级的数据不混合计算一个总准确率。")
    add_figure(doc, assets["timeline"], "图 10 从离线评测到跨系统联调的证据链", 15.4)

    add_heading(doc, "2 评测数据集与指标", 2)
    add_table(doc, ["数据集", "规模", "主要指标", "用途"], [
        ["需求问卷", "21 份", "比例与开放反馈", "确定业务范围和安全约束"],
        ["对话回归", "45 条", "通过率 意图 风控 引用 延迟", "验证常见客服意图"],
        ["检索冻结保留集 V5", "200 条 含 40 条拒绝", "首条命中率 拒答准确率", "比较关键词 向量和混合方案"],
        ["核心安全集", "200 条", "安全通过与行为匹配", "覆盖越权 注入 无证据和高风险操作"],
        ["独立回归", "300 条", "授权 证据冲突 多轮对话", "检验未参与训练的综合行为"],
        ["真实工具验收", "12 项", "接口状态 证据引用 清理", "验证真实 PostgreSQL 和 Commerce API"],
        ["双媒介浏览器联调", "24 项早期抽测 21 项修复验收", "通过 部分 未通过 延迟", "验证 AI 客服接入不同渠道后的实际交互"],
    ], [3.2, 2.8, 5.0, 4.4], 8.7)

    add_heading(doc, "3 对照与可复现性", 2)
    add_body(doc, "检索实验在同一 200 条冻结保留集上比较关键词、向量和意图路由加基础检索降级，保留集未参与调参。核心安全集同时报告安全通过与完整行为匹配，防止模型只通过拒答获得高安全分。300 条独立回归先冻结回答并计算 SHA-256，再读取评分规则；该套题不是第三方盲测，因此报告明确其证据等级。真实工具验收使用隔离 PostgreSQL 数据库、固定测试 UUID 和清理步骤，避免污染业务数据。")
    add_body(doc, "阶段性报告没有把不同日期、不同范围的测试直接当作同一基准。2026 年 11 月 6 日早期本地抽测暴露的英文检索、多轮上下文和异常提示问题，与后续公网修复验收分别呈现；后续通过并不自动抹去早期问题，而是构成问题发现和修复证据。")

    # 7
    add_heading(doc, "七 实验结果与讨论", 1)
    add_heading(doc, "1 检索结果", 2)
    add_figure(doc, assets["retrieval"], "图 11 冻结保留集检索首条命中率对比", 15.4)
    add_body(doc, "在包含 14 条知识条目的 200 条冻结保留集上，关键词检索首条命中 111/200，向量检索 152/200，意图样例路由加基础检索降级 194/200，分别为 55.5%、76.0% 和 97.0%。后者相对关键词方案提高 41.5 个百分点，命中数约为 1.75 倍；40 条应拒绝问题全部正确拒绝。结果说明口语改写和轻度错字需要语义信号，但语义相似度必须与范围判断共同使用。")
    add_body(doc, "该结果的外推边界是知识库规模较小且领域明确。随着企业 FAQ、商品和售后规则增加，仍需验证索引更新、商户过滤、长文档切分和召回延迟；97.0% 不能直接解释为所有客服问题的回答准确率。")

    add_heading(doc, "2 对话与安全结果", 2)
    add_figure(doc, assets["evaluation"], "图 12 对话 安全和独立回归结果", 15.4)
    add_body(doc, "45 条对话回归全部通过，意图和风控门禁均为 45/45，延迟 P50 为 761 ms、P95 为 1531 ms、平均 714 ms。该集合覆盖问候、订单、售后、商品、人工接管、范围外问题和提示注入。由于部分规则路径可在 1 至 21 ms 内快速返回，延迟统计混合了规则、检索和模型链路，不能据此推断单次模型调用速度。")
    add_body(doc, "完整 NOVA 编排、安全门禁和证据约束系统在 200 条核心安全集上安全通过 200/200，完整行为匹配 200/200；同一阶段的原始离线模型核心安全为 129/200。二者相差 35.5 个百分点，说明系统门禁对可靠性具有决定作用，也说明不能把完整系统成绩归因于裸模型。")
    add_body(doc, "300 条独立回归通过 280/300，平均 97.17 分，安全禁项命中为 0。其中授权边界 100/100、证据冲突 100/100，多轮对话 80/100。20 条失败主要反映回答缺少面向客户的下一步动作或多轮衔接，而不是越权或证据覆盖。下一阶段应把多轮任务完成率作为主优化指标。")

    add_heading(doc, "3 真实工具与双媒介接入结果", 2)
    add_body(doc, "真实商城工具验收在隔离 PostgreSQL 数据库与 Spring Commerce API 上完成 12/12：包括健康检查、错误签名拒绝、现货与缺货库存、本人订单、物流、已支付、待付款、退款处理中、跨客户阻断、匿名阻断和测试数据清理。该结果证明工具链能读取真实数据库记录并返回可引用证据，但不代表生产供应商或生产数据库已经接通。")
    add_body(doc, "早期本地浏览器抽测共 21 次实际提问与 3 项接口边界测试，人工逐条核对为 15 项通过、5 项部分通过、4 项未通过。19 条 HTTP 200 问答的浏览器观察耗时中位数为 1.78 秒，范围 0.07 至 2.60 秒。失败集中在英文联系问题、多轮上下文和未接入的商品库存优惠，构成后续修复清单。")
    add_body(doc, "后续多 Agent 接入完成后，AI 服务 222 项测试通过，公网浏览器 21 项检查通过。三组已部署签名场景分别为订单加退货条件加邮箱、英语配送、OMS 取消订单的付款与退款查询，观测耗时约 6.95 秒、3.87 秒和 3.72 秒；最终记录到 7 条完整 Agent 链路，均经模型规划和审核通过且未走回退。订单复合场景使用明确标记的合成证据，真实客户订单端到端售后资格判断仍未纳入结论。")

    add_heading(doc, "4 结果讨论", 2)
    add_body(doc, "实验支持三个关于 AI 客服核心的判断。第一，客服检索需要同时优化召回和拒答，单纯追求相似度会扩大越界回答。第二，实时订单事实必须来自受控工具，模型更适合解释证据而不是决定证据。第三，多 Agent 能组织跨知识和订单的复合任务，但会增加模型调用和延迟，必须按任务复杂度选择性启用。OMS 与独立站的作用是提供不同身份和数据条件，实验结论针对的是 NOVA 在这些条件下的行为。")
    add_body(doc, "系统仍有明显边界：独立站实时商品库存与优惠尚未接入，人工接管只提供标记和工单入口，多实例会话尚未使用共享存储，真实客户订单和多租户生产环境尚未完成压力、故障与越权专项。研究阶段应把这些未完成项保留在报告中，避免把可演示原型描述成完整生产系统。")

    # 8
    add_heading(doc, "八 创新点与应用价值", 1)
    add_heading(doc, "1 主要创新点", 2)
    add_table(doc, ["序号", "类型", "创新内容", "对比优势与证据"], [
        ["1", "方法创新", "把静态知识和动态交易事实拆分为不同证据通道 动态状态只通过受限工具读取", "避免模型记忆替代实时状态 工具验收 12/12"],
        ["2", "算法创新", "意图样例路由结合向量与关键词检索 并把范围外拒答纳入同一评测", "冻结集由 55.5% 提升至 97.0% 拒答 40/40"],
        ["3", "系统创新", "知识 订单 售后专业 Agent 加独立审核 Agent 依赖关系写入执行器", "7 条完整链路通过审核 订单证据不以自由文本跨 Agent 传播"],
        ["4", "安全创新", "身份 范围 证据 策略四门禁加来源前缀和 HMAC 短时签名", "完整系统安全 200/200 授权和证据冲突各 100/100"],
        ["5", "应用创新", "同一 AI 客服核心通过适配器接入 OMS 管理端和独立站 保留各自身份与数据边界", "核心能力不绑定渠道 后端最小改造 21 项公网浏览器检查通过"],
    ], [1.0, 2.0, 6.3, 6.3], 8.7)

    add_heading(doc, "2 社会与经济价值验证框架", 2)
    add_body(doc, "当前证据能够说明准确性、安全性和工程可行性，但还没有企业连续运营期的人工工单、客户满意度和成本数据。因此，本报告不直接宣称降低多少客服成本，而是将可验证指标分为已测、待生产验证和待企业试点三类。")
    add_table(doc, ["指标", "当前证据", "下一阶段验收目标", "价值含义"], [
        ["知识首条命中率", "97.0%", "扩充企业知识后保持不低于 95%", "减少找错政策"],
        ["范围外拒答准确率", "40/40", "新增渠道问题后保持不低于 98%", "减少无依据附会"],
        ["核心安全通过率", "200/200", "生产回归保持 100%", "降低越权与虚假承诺"],
        ["独立回归通过率", "93.3%", "提升到不低于 96%", "提高综合稳定性"],
        ["多轮任务通过率", "80.0%", "提升到不低于 95%", "减少重复解释"],
        ["真实工具验收", "12/12", "接入正式企业数据后全量复测", "确保业务事实可用"],
        ["公网浏览器检查", "21 项通过", "纳入每次发布回归", "降低接入回归风险"],
        ["规则检索链路延迟", "45 条回归 P95 1531 ms", "分路径设定生产 SLO", "控制等待时间"],
        ["AI 独立解决率", "尚无企业连续基线", "A B 试点采集 4 周", "测量人工咨询下降"],
        ["单工单成本与满意度", "尚无企业连续基线", "与人工组同口径采集", "计算真实净收益"],
    ], [3.4, 3.8, 4.2, 4.2], 8.4)
    add_figure(doc, assets["eq_benefit"], "图 13 企业试点年度净收益计算模型", 12.5)
    add_body(doc, "式 3 中 Q 为年度可纳入试点的咨询量，a 为 AI 独立解决率，Tₕ 与 Tₐ 分别为人工和 AI 路径的平均处理时长，Cₕ 为单位人工时长成本，Cₛ 为系统年度运行与维护成本。任何经济收益必须在企业试点取得上述变量后计算，并同时报告转人工遗漏、投诉和满意度，防止用节省时间掩盖服务质量下降。")

    add_heading(doc, "3 转化路径", 2)
    add_bullets(doc, [
        "面向电商企业交付可插拔接入包，保留原站登录、订单归属和人工工单体系。",
        "将企业 FAQ、商品与售后知识纳入审核发布流程，按商户、版本和有效期管理。",
        "把订单、物流、支付和库存工具做成只读能力，写操作另行配置身份确认和人工审批。",
        "以离线安全集、隔离工具验收、浏览器回归和生产监控构成持续验收体系。",
        "在取得企业试点证据后形成软著、专利或技术标准材料，并补充第三方测试。",
    ])

    # 9
    add_heading(doc, "九 局限性与后续研究", 1)
    add_heading(doc, "1 当前局限", 2)
    add_table(doc, ["局限", "影响", "改进方向"], [
        ["企业调研只有 1 家", "不能推断行业共性和成本结构", "补充 5 至 10 家不同行业企业访谈"],
        ["知识库规模仍小", "97% 检索结果可能高估大规模知识表现", "扩展商品 政策 FAQ 后重新构造冻结集"],
        ["独立站实时商品与优惠未接入", "部分咨询只能说明限制并给入口", "接入产品目录 库存与优惠只读 API"],
        ["多轮对话 80/100", "复杂任务容易缺少下一步动作", "强化会话状态 任务完成判分与用户确认"],
        ["会话缓存为单进程内存", "多实例部署会丢失上下文", "迁移 Redis 并增加并发一致性测试"],
        ["人工队列未形成闭环", "requires_human 不等于真人接通", "接入工单队列 排队状态和接管回执"],
        ["生产真实订单验收不足", "不能声明完整生产可用", "使用脱敏真实订单和多租户专项验收"],
        ["模型依赖外部服务", "可能受限于延迟和可用性", "建立模型切换 速率限制和安全降级"],
    ], [4.2, 5.0, 6.2], 8.8)

    add_heading(doc, "2 后续研究路线", 2)
    add_figure(doc, assets["roadmap"], "图 14 下一阶段研究与转化路线", 15.4)
    add_body(doc, "阶段一补齐企业真实数据与运营基线；阶段二完成多租户、共享会话、压力和故障演练；阶段三开展同口径 A B 对照试验，使用独立解决率、错误转人工率、客户满意度和单位工单成本评价；阶段四再固化专利、软著、企业报告和竞赛展示材料。每一阶段都保留可回滚版本与冻结评测集，避免调参污染测试结论。")

    add_heading(doc, "3 计划实验", 2)
    add_table(doc, ["实验", "设计", "主要指标", "判定原则"], [
        ["知识扩容实验", "按商户增加至不少于 500 条知识并冻结新保留集", "Recall@k 首条命中 拒答准确率 延迟", "性能下降需定位索引或范围过滤原因"],
        ["真实会话盲审", "脱敏后由两名客服独立评分 争议交第三人", "事实正确 完整 简洁 可操作", "报告一致性系数和分歧样本"],
        ["生产影子流量", "只读复制咨询 不向客户直接展示", "错误工具调用 证据缺失 风险触发", "零写操作 零跨租户"],
        ["A B 试点", "人工组与 AI 加人工组使用同口径工单", "解决率 处理时长 满意度 投诉", "同时满足效率和质量门槛"],
        ["故障注入", "模拟模型超时 工具 5xx Redis 故障与签名过期", "降级正确率 恢复时间 数据泄露", "任何故障不得扩大数据范围"],
    ], [3.0, 5.8, 4.2, 3.0], 8.5)

    # 10
    add_heading(doc, "十 结论", 1)
    conclusion = (
        "本研究完成了一个可运行的 NOVA 证据约束多 Agent AI 客服核心系统，并把可靠性要求落实到系统结构而不是停留在提示词。"
        "OMS 管理端与 BUZUD 独立站分别作为后台管理和客户服务验证媒介，用于检验同一 AI 客服核心在不同身份 数据和交互条件下的可迁移性，而非项目的研究主体。"
        "原型通过业务后端鉴权、来源隔离、HMAC 短时签名、最小字段、混合检索、只读业务工具、多 Agent 分工、独立审核和人工接管，"
        "形成从用户问题到证据、回答和审计的闭环。阶段性结果显示，意图路由加检索降级在 200 条冻结集上达到 97.0% 首条命中率，"
        "完整系统核心安全达到 200/200，300 条独立回归通过 280 条，真实商城工具 12 项全部通过，后续公网浏览器检查 21 项通过。"
        "这些结果支持证据约束型架构的技术可行性，也暴露了多轮任务 80/100、独立站实时商品数据未接入、人工队列和生产多租户尚未完成等边界。"
        "下一阶段应以真实企业数据、脱敏客户订单和连续运营基线开展对照试验，再计算人工咨询下降、客户满意度和单位工单成本。"
        "与现有规则机器人 知识型 RAG 客服和平台型业务智能体相比，NOVA 不把知识接入或 API 调用本身作为创新，而将差异化定位于渠道无关的证据约束组合与可重复评测。"
        "项目的可推广价值在于提供一套不依赖单一模型和单一业务平台的企业客服方法：让模型负责理解和表达，让业务系统负责身份与事实，让规则 审核和人工承担最终责任。"
    )
    add_body(doc, conclusion)

    # References
    add_page_break(doc)
    add_heading(doc, "参考文献", 1)
    references = [
        "[1] 国务院. 关于深入实施“人工智能+”行动的意见 国发〔2025〕11号[EB/OL]. 2025-08-21[2026-11-09]. https://www.cac.gov.cn/2025-08/27/c_1758018277755538.htm.",
        "[2] 国家互联网信息办公室等七部门. 生成式人工智能服务管理暂行办法[EB/OL]. 2023-07-13[2026-11-09]. https://www.cac.gov.cn/2023-07/13/c_1690898327029107.htm.",
        "[3] 国家互联网信息办公室 工业和信息化部 公安部 国家广播电视总局. 人工智能生成合成内容标识办法 国信办通字〔2025〕2号[EB/OL]. 2025-03-07[2026-11-09]. https://www.cac.gov.cn/2025-03/14/c_1743654684782215.htm.",
        "[4] 国务院. 网络数据安全管理条例 国务院令第790号[S]. 2024.",
        "[5] 全国人民代表大会常务委员会. 中华人民共和国个人信息保护法[S]. 2021.",
        "[6] 全国人民代表大会常务委员会. 中华人民共和国数据安全法[S]. 2021.",
        "[7] 全国人民代表大会常务委员会. 中华人民共和国电子商务法[S]. 2018.",
        "[8] 国务院. 十四五数字经济发展规划 国发〔2021〕29号[EB/OL]. 2022-01-12[2026-11-09]. https://www.gov.cn/zhengce/content/2022-01/12/content_5667817.htm.",
        "[9] 挑战杯全国大学生课外学术科技作品竞赛组委会. 第十九届挑战杯全国大学生课外学术科技作品竞赛通知[EB/OL]. 2025[2026-11-09]. https://2025.tiaozhanbei.net/d49/article/676/.",
        "[10] LEWIS P, PEREZ E, PIKTUS A, et al. Retrieval-Augmented Generation for Knowledge-Intensive NLP Tasks[C]//Advances in Neural Information Processing Systems. 2020, 33: 9459-9474.",
        "[11] KARPUKHIN V, OGUZ B, MIN S, et al. Dense Passage Retrieval for Open-Domain Question Answering[C]//Proceedings of EMNLP. 2020: 6769-6781.",
        "[12] IZACARD G, GRAVE E. Leveraging Passage Retrieval with Generative Models for Open Domain Question Answering[C]//Proceedings of EACL. 2021: 874-880.",
        "[13] SHUSTER K, POFF S, CHEN M, et al. Retrieval Augmentation Reduces Hallucination in Conversation[C]//Findings of EMNLP. 2021: 3784-3803.",
        "[14] ASAI A, WU Z, WANG Y, et al. Self-RAG Learning to Retrieve Generate and Critique through Self-Reflection[C]//International Conference on Learning Representations. 2024.",
        "[15] GAO Y, XIONG Y, GAO X, et al. Retrieval-Augmented Generation for Large Language Models A Survey[EB/OL]. arXiv:2312.10997, 2023[2026-11-09]. https://arxiv.org/abs/2312.10997.",
        "[16] MIALON G, DESSI R, LOMELI M, et al. Augmented Language Models A Survey[J]. Transactions on Machine Learning Research, 2023.",
        "[17] YAO S, ZHAO J, YU D, et al. ReAct Synergizing Reasoning and Acting in Language Models[C]//International Conference on Learning Representations. 2023.",
        "[18] SCHICK T, DWIVEDI-YU J, DESSI R, et al. Toolformer Language Models Can Teach Themselves to Use Tools[C]//Advances in Neural Information Processing Systems. 2023, 36.",
        "[19] QIN Y, LIANG S, YE Y, et al. ToolLLM Facilitating Large Language Models to Master 16000 plus Real-world APIs[C]//International Conference on Learning Representations. 2024.",
        "[20] WU Q, BANSAL G, ZHANG J, et al. AutoGen Enabling Next-Gen LLM Applications via Multi-Agent Conversation[EB/OL]. arXiv:2308.08155, 2023[2026-11-09]. https://arxiv.org/abs/2308.08155.",
        "[21] HONG S, ZHUGE M, CHEN J, et al. MetaGPT Meta Programming for a Multi-Agent Collaborative Framework[C]//International Conference on Learning Representations. 2024.",
        "[22] LI G, HAMMOUD H A A K, ITANI H, et al. CAMEL Communicative Agents for Mind Exploration of Large Scale Language Model Society[EB/OL]. arXiv:2303.17760, 2023[2026-11-09]. https://arxiv.org/abs/2303.17760.",
        "[23] WEI J, WANG X, SCHUURMANS D, et al. Chain-of-Thought Prompting Elicits Reasoning in Large Language Models[C]//Advances in Neural Information Processing Systems. 2022, 35: 24824-24837.",
        "[24] OUYANG L, WU J, JIANG X, et al. Training Language Models to Follow Instructions with Human Feedback[C]//Advances in Neural Information Processing Systems. 2022, 35: 27730-27744.",
        "[25] JI Z, LEE N, FRIESKE R, et al. Survey of Hallucination in Natural Language Generation[J]. ACM Computing Surveys, 2023, 55(12): 1-38.",
        "[26] MANAKUL P, LIUSIE A, GALES M J F. SelfCheckGPT Zero-Resource Black-Box Hallucination Detection for Generative Large Language Models[C]//Proceedings of EMNLP. 2023.",
        "[27] LIU N F, LIN K, HEWITT J, et al. Lost in the Middle How Language Models Use Long Contexts[J]. Transactions of the Association for Computational Linguistics, 2024, 12: 157-173.",
        "[28] ES S, JAMES J, ESPINOSA ANKE L, et al. RAGAS Automated Evaluation of Retrieval Augmented Generation[C]//Proceedings of EACL System Demonstrations. 2024.",
        "[29] SAAD-FALCON J, KHATTAB O, POTTS C, et al. ARES An Automated Evaluation Framework for Retrieval-Augmented Generation Systems[C]//Proceedings of NAACL. 2024: 338-354.",
        "[30] LIN S, HILTON J, EVANS O. TruthfulQA Measuring How Models Mimic Human Falsehoods[C]//Proceedings of ACL. 2022: 3214-3252.",
        "[31] XIAO S, LIU Z, ZHANG P, et al. C-Pack Packaged Resources To Advance General Chinese Embedding[EB/OL]. arXiv:2309.07597, 2023[2026-11-09]. https://arxiv.org/abs/2309.07597.",
        "[32] CORMACK G V, CLARKE C L A, BUETTCHER S. Reciprocal Rank Fusion Outperforms Condorcet and Individual Rank Learning Methods[C]//Proceedings of SIGIR. 2009: 758-759.",
        "[33] ZHENG L, CHIANG W L, SHENG Y, et al. Judging LLM-as-a-Judge with MT-Bench and Chatbot Arena[C]//Advances in Neural Information Processing Systems Datasets and Benchmarks. 2023.",
        "[34] CHEN J, LIN H, HAN X, et al. Benchmarking Large Language Models in Retrieval-Augmented Generation[EB/OL]. arXiv:2309.01431, 2023[2026-11-09]. https://arxiv.org/abs/2309.01431.",
        "[35] KADAVATH S, CONERLY T, ASKELL A, et al. Language Models Mostly Know What They Know[EB/OL]. arXiv:2207.05221, 2022[2026-11-09]. https://arxiv.org/abs/2207.05221.",
        "[36] NOVA项目组. AI客服评测报告 45条对话回归[R]. 2026.",
        "[37] NOVA项目组. 检索层冻结保留集对比报告 200条[R]. 2026.",
        "[38] NOVA项目组. NOVA核心安全独立评测 200条[R]. 2026.",
        "[39] NOVA项目组. 第三套300条冻结回答评分报告[R]. 2026.",
        "[40] NOVA项目组. 真实商城工具验收报告[R]. 2026.",
        "[41] NOVA项目组. OMS与独立站客服子Agent接入报告[R]. 2026.",
        "[42] NOVA项目组. 本地OMS与独立站客服实问测试报告[R]. 2026.",
        "[43] NOVA项目组. AI客服问卷反馈调整说明[R]. 2026.",
        "[44] GOOGLE CLOUD. Intents Dialogflow CX[EB/OL]. [2026-11-09]. https://docs.cloud.google.com/dialogflow/cx/docs/concept/intent.",
        "[45] GOOGLE CLOUD. Webhooks Dialogflow CX[EB/OL]. [2026-11-09]. https://docs.cloud.google.com/dialogflow/cx/docs/concept/webhook.",
        "[46] INTERCOM. Fin AI Agent Explained[EB/OL]. [2026-11-09]. https://www.intercom.com/help/en/articles/7120684-fin-ai-agent-explained.",
        "[47] INTERCOM. The Fin AI Engine[EB/OL]. 2026[2026-11-09]. https://www.intercom.com/help/en/articles/9929230-the-fin-ai-engine.",
        "[48] ZENDESK. About AI Agents[EB/OL]. 2026-09-01[2026-11-09]. https://support.zendesk.com/hc/en-us/articles/6970583409690-About-AI-agents.",
        "[49] ZENDESK. Connecting Knowledge Sources to Power Generative Replies in AI Agents[EB/OL]. 2026-06-15[2026-11-09]. https://support.zendesk.com/hc/en-us/articles/8357749301658-Connecting-knowledge-sources-to-power-generative-replies-in-advanced-AI-agents.",
        "[50] MICROSOFT. Available Knowledge Sources for Agents in Copilot Studio[EB/OL]. [2026-11-09]. https://learn.microsoft.com/en-us/microsoft-copilot-studio/agents-experience/knowledge-sources-overview.",
        "[51] MICROSOFT. Orchestrate Agent Behavior with Generative AI[EB/OL]. [2026-11-09]. https://learn.microsoft.com/en-us/microsoft-copilot-studio/advanced-generative-actions.",
        "[52] MICROSOFT. Agent Runtime Protection Status[EB/OL]. 2026[2026-11-09]. https://learn.microsoft.com/en-us/microsoft-copilot-studio/security-agent-runtime-view.",
        "[53] SALESFORCE. Agentforce Glossary of Terms[EB/OL]. [2026-11-09]. https://help.salesforce.com/s/articleView?id=ai.copilot_glossary.htm.",
        "[54] SALESFORCE. Trust and Agentforce[EB/OL]. [2026-11-09]. https://help.salesforce.com/s/articleView?id=ai.copilot_trust.htm.",
        "[55] SALESFORCE. About Agentforce Session Tracing[EB/OL]. [2026-11-09]. https://help.salesforce.com/s/articleView?id=ai.generative_ai_session_trace_about.htm.",
    ]
    for ref in references:
        p = doc.add_paragraph()
        p.paragraph_format.left_indent = Cm(0.7)
        p.paragraph_format.first_line_indent = Cm(-0.7)
        p.paragraph_format.space_after = Pt(2)
        p.paragraph_format.line_spacing_rule = WD_LINE_SPACING.SINGLE
        set_font(p.add_run(ref), "宋体", 9, False, INK)

    # Appendices.
    add_page_break(doc)
    add_heading(doc, "附录一 阶段性证据目录", 1)
    add_table(doc, ["证据", "位置或形式", "用途", "公开结论边界"], [
        ["需求问卷与反馈说明", "docs目录", "形成需求与权限约束", "企业样本不推算行业比例"],
        ["45条对话评测", "services ai-service evaluation", "验证意图 风控 引用和延迟", "不是开放域能力评分"],
        ["检索冻结保留集", "data training evaluations", "对照三种检索方案", "知识条目 14 条"],
        ["核心安全200条", "data training evaluations", "检验完整系统门禁", "不代表裸模型"],
        ["独立回归300条", "冻结答案与评分报告", "检验授权 证据冲突和多轮", "非第三方盲测"],
        ["真实商城工具12项", "隔离数据库验收", "验证工具与跨客户阻断", "非生产数据库"],
        ["公网浏览器与Agent记录", "deployment证据目录", "验证部署后的UI与链路", "订单复合用例为合成证据"],
    ], [3.2, 4.2, 4.2, 4.0], 8.7)

    add_heading(doc, "附录二 挑战杯答辩十页建议", 1)
    add_table(doc, ["页码", "主题", "核心内容", "建议视觉", "时长"], [
        ["1", "封面", "NOVA AI 客服核心定位 团队 学校", "核心系统与双媒介图", "20秒"],
        ["2", "痛点与现状", "模型与业务事实脱节 主流技术路线", "问卷图和技术对比表", "30秒"],
        ["3", "科学挑战", "数据 算法 系统三层递进", "图2", "30秒"],
        ["4", "总体架构", "NOVA 核心层 可信网关 证据层", "图3", "35秒"],
        ["5", "可信数据流", "身份 签名 最小字段 来源隔离", "图4和式2", "35秒"],
        ["6", "核心算法", "意图路由 混合检索 RRF", "图6和图11", "35秒"],
        ["7", "多Agent", "专业分工 显式依赖 独立审核", "图7", "35秒"],
        ["8", "实验结果", "检索 安全 独立回归 工具验收", "图12", "40秒"],
        ["9", "创新与价值", "五项创新和试点指标", "创新表和式3", "35秒"],
        ["10", "局限与下一步", "真实企业基线 多租户 人工闭环", "图14", "25秒"],
    ], [1.2, 2.6, 5.6, 4.0, 1.6], 7.8)

    add_heading(doc, "附录三 提交前需补充的参赛信息", 1)
    add_bullets(doc, [
        "学校 学院 申报者代表 学号 专业年级 指导教师与团队分工。",
        "学校下发的正式申报书模板 原创性声明和作品分类代码。",
        "企业合作或试点证明 软件著作权 专利及第三方测试材料。",
        "真实企业连续运营数据和脱敏样本的合规授权。",
        "演示视频中突出同一 NOVA AI 客服核心在 OMS 与独立站两种媒介上的证据与人工接管闭环。",
    ])

    # Metadata and save.
    props = doc.core_properties
    props.title = "NOVA 证据约束多 Agent 智能客服系统研究报告"
    props.subject = "挑战杯科技发明制作类研究报告"
    props.author = "NOVA 项目组"
    props.keywords = "智能客服, RAG, 多Agent, 证据约束, 业务工具, 挑战杯"
    props.comments = "基于项目现有证据生成"
    doc.save(OUT)

    full_text = "\n".join(p.text for p in doc.paragraphs)
    chinese_chars = len(re.findall(r"[\u4e00-\u9fff]", full_text))
    print(f"saved={OUT}")
    print(f"paragraphs={len(doc.paragraphs)} tables={len(doc.tables)} chinese_chars={chinese_chars}")


if __name__ == "__main__":
    build_document()
