# Near

# Near

# 团队介绍

**Alexander Skidanov** Co-Founder. Joined Microsoft in 2009\. Joined MemSQL in 2011 as Engineer. He has two ICPC medals (gold in 2008 and bronze in 2005).[https://x.com/alexskidanov](https://x.com/alexskidanov)

**Illia Polosukhin**  
Co-Founder. He previously worked on the MemSQL, Google AI, and Tensorflow teams. Major contributor to TensorFlow.A former ICPC finalist.[https://x.com/ilblackdragon](https://x.com/ilblackdragon)

# 融资情况

| 融资轮次 | 时间 | 融资金额 | 估值 | 领投机构 |
| :---- | :---- | :---- | :---- | :---- |
| \-- | 2019-07-10 | $ 12.1M | $120M | Accomplice\*, MetaStable Capital\*, |
| \-- | 2020-05-04 | $ 21.6M | $250M | Andreessen Horowitz\* |
| OTC  2022 | 2022-01-13 | $ 150M  | Unknown | Cobo Ventures |
| OTC  2022 | 2022-04-06 | $ 350M | Unknown | The Spartan Group\*, gumi Cryptos Capital\* |

18年成立;  2020年10月上线主网，20年10月TGE，目前 FDV $3.7B

# 社区情况

截至2025.3.27  
X 粉丝数 1.8M  
Discord 71K  
Telegram 5.9w粉丝

# 技术分析

Near是一条高性能分片区块链，基于Pos共识算法

Near的账户模型与其他区块链有较大区别，用户通过NEAR账户参与NEAR生态系统。这些账户由唯一地址标识，可选择性地持有智能合约，并通过访问密钥进行控制。

## Named Account & Account Abstraction

NEAR**原生**实现两种类型的账户：

1. **命名账户**，如`alice.near`，易于记忆和分享，并且可以创建子账户  
2. **隐式账户**，如`0xfb9243ce...`，从私钥派生而来,64位字符

NEAR账户可以拥有多个密钥，每个密钥都有自己的权限集：

* 如果一个密钥被泄露，您可以轻松更换  
* 您可以将密钥用作第三方应用程序的授权令牌

***与以太坊账户的比较***

|  | 以太坊账户 | NEAR账户 |
| ----- | ----- | ----- |
| 账户ID | 公钥 ( 0x123... ) | \- 原生命名账户 (alice.near) \- 隐式账户 ( 0x123... ) |
| 密钥 | 私钥 ( 0x456... ) | 多个密钥对，具有不同权限：\- Full-Access 密钥（完全访问权限） \- Function-Call 密钥（仅调用功能的有限权限，如对指定合约的调用进行签名） |
| 智能合约 | 同步执行，账户调用智能合约 | 异步执行，账户可以选择性地持有应用程序 |
| Gas费用 | 以美元计算 | 以美分的十分之一计算 |
| 区块时间 | \~12秒 | \~1.3秒 |

## Near’s Chain Abstraction

NEAR的链抽象框架由三项核心技术组成，这些技术共同构建了一个框架，旨在使区块链互操作性更加便捷，让开发者能够创建真正的跨链应用，同时使终端用户享受简化的体验，而不必关心底层的复杂技术实现。

* NEAR Intents  
* Chain Signatures  
* Omni Bridge

### NEAR Intents

一种新的交易模式，允许用户只需表达“意图”（比如"以最佳价格交换代币"），而不必处理具体的技术细节。系统会自动为他们找到最佳方案。

工作原理如下：

1. 用户提交“意图”：表达期望而无需指定细节  
2. 解决者网络竞争：一个去中心化的solver网络（包括AI Agent和Market Maker）竞争接收任务  
3. 跨链执行：胜出的Solver以最佳解决方案执行，可能涉及跨链

### Chain Signatures

这项技术使NEAR账户能够在其他区块链（如比特币或以太坊）上签署和执行交易。通过多方计算技术(MPC)，一个NEAR账户可以控制多个区块链上的资产和账户，极大地简化了开发跨链应用的复杂度。

在Near上可以编写直接签署跨链交易的智能合约，利用去中心化MPC进行无信任签名生成

### Omni Bridge

一个高效的跨链资产转移系统，它结合了链签名技术和特定链的验证方法，大大缩短了传统桥的验证时间（从小时级到分钟级），同时降低了gas费用。  
当前支持Ethereum，Bitcoin，Solana，Base，Arbitrum。  
