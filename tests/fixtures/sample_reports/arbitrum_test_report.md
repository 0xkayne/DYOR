---
project_name: Arbitrum
track: Layer2
date: "2024-01-15"
author: "研究员A"
keywords:
  - Layer2
  - Optimistic Rollup
  - ARB
---

# Arbitrum 深度研究报告

Analyst: 研究员A

## 项目概述

Arbitrum 是由 Offchain Labs 开发的 Optimistic Rollup Layer 2 扩展解决方案，
部署在以太坊主网之上。项目旨在通过将交易计算移至链下，大幅降低 Gas 费用并提升
吞吐量，同时继承以太坊的安全性。

报告日期：2024-01-15

![Arbitrum 架构图](images/architecture.png)

## 团队背景

Offchain Labs 由三位创始人共同创立：

- **Ed Felten**：普林斯顿大学计算机科学教授，前白宫科技政策办公室副主任，
  在密码学和系统安全领域拥有深厚积累。
- **Steven Goldfeder**：普林斯顿大学博士，区块链安全与密码学研究员。
- **Harry Kalodner**：普林斯顿大学博士，专注于区块链协议研究。

团队学术背景扎实，工程执行力强，已完成多轮融资，投资方包括 Pantera Capital 和
Polychain Capital。

<img src="images/team.jpg" alt="Offchain Labs 团队" />

## 技术分析

Arbitrum 采用 Optimistic Rollup 架构，默认认为所有交易均有效，只在受到挑战时
才进行欺诈证明验证。挑战期为 7 天，这是提款至以太坊主网的等待时间。

相比以太坊主网，Arbitrum 可将 Gas 费用降低约 90-95%，理论 TPS 可达 40,000+。
Arbitrum One 是主要的公共链，Arbitrum Nova 则针对高频低价值交易场景（如游戏）。

Stylus 升级引入了 WebAssembly (WASM) 支持，允许开发者使用 Rust、C++ 等语言
编写智能合约，显著扩展了开发者生态。

## 代币经济学

ARB 代币于 2023 年 3 月空投，总量 100 亿枚：

- 团队与顾问：26.94%（有锁仓期）
- 投资者：17.53%（有锁仓期）
- DAO 治理金库：42.78%
- 空投用户：11.62%
- 生态基金：1.13%

流通量约 12.75 亿枚（截至 2024-01-15）。ARB 主要用于 Arbitrum DAO 的链上治理投票。
2024-03-16 将有大量团队与投资者代币解锁，需关注潜在抛压。

## 风险因素

1. **竞争风险**：Optimism、zkSync、StarkNet 等 L2 竞争激烈，市场份额存在争夺。
2. **技术风险**：智能合约漏洞、跨链桥攻击风险，历史上桥接合约曾发生安全事件。
3. **代币解锁压力**：2024 年多次大额解锁可能带来短期价格压力。
4. **监管不确定性**：全球加密货币监管环境存在不确定性，可能影响项目运营。
5. **中心化风险**：Sequencer 目前由 Offchain Labs 单一运营，存在潜在中心化问题。
