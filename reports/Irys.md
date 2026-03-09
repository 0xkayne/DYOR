# Irys & 去中心化存储的前世今生

 《去中心化存储的前世今生》 先分析最新的去中心化存储项目 Irys ，再横向对比自 Filecoin 以来的项目，包括 Filecoin, StorJ, Crust Network, Arweave, CESS, Walrus；主要对比以下几个方面：1.存储架构（链上链下）2.存储费用定价 3.网络角色分工 4.数据获取效率 5.数据可靠性 6.相关生态应用 

## 融资背景

| 时间 | 金额 | 估值 | 轮次 | VC |
| :---- | :---- | :---- | :---- | :---- |
| 2022 年 5 月 | $ 5.2 M | unknown | unknown | Framework Ventures, Hypersphere Ventures, Permanent Ventures 领投 |
| 2024 年 6 月 | $ 3.5 M | unknown | Strategic | Lemniscap 领投 |

Irys 前身为 Bundlr Network，是 Arweave 内最大的生态项目，作为存储数据的溯源层，打包上传的数据量占 AR 网络的 80% 左右；目前 X 粉丝 239k ， Discord 74k 粉丝（活跃人数10%）

## 团队背景

| 人物 | 职位 | 履历 | 社媒链接 | 特殊情况 |
| :---- | :---- | :---- | :---- | :---- |
| Josh Benaron | Founder & CEO | 毕业于萨里大学 2021 年 5 月开始做 Irys 项目 | X@josh\_benaron 粉丝12k |  |
| Jesse Wright | Lead Engineer |  | github:[https://github.com/JesseTheRobot](https://github.com/JesseTheRobot)  | Rust & TS |
| Gus Lobo | CMO | 曾在Scrib3任职总经理 | X@misterwestwolf 粉丝4k |  |
| Faris Oweis | AI Lead | 2023 年 1 月至今在 Eclipse 任职 BD Lead；同时 2024 年 12 月开始，至今在 Irys 任职 AI Lead；奥本大学哈伯特商学院 | X@faris\_says 粉丝1.3k Linkedin [https://www.linkedin.com/in/farisoweis/](https://www.linkedin.com/in/farisoweis/)   | SVM Maxi |
| Dan MacDonald | Protocol Lead | 毕业于维多利亚大学，曾在 Arweave 协议担任专家 | X@DMacOnchainLinkedin [https://www.linkedin.com/in/danmacd/?originalSubdomain=ca](https://www.linkedin.com/in/danmacd/?originalSubdomain=ca) Github [https://github.com/DanMacDonald](https://github.com/DanMacDonald) |  |
| Tiffany L. | 生态副主席 | 曾在0G Labs, Avalanche,Apple工作，毕业于南加州大学目前在 Datagram Network 战略顾问 | X@tiffanylai\_ 粉丝 3k Linkedin [https://www.linkedin.com/in/tlai319/](https://www.linkedin.com/in/tlai319/) |  |
| Nick Galang | Creative Director  |  | X@0xGala粉丝 2.7k |  |

## 产品核心

Irys 的核心定位是 Datachain，相比于其他存储协议，使得存储的数据具有使用价值和可编程性，Irys 通过构建原生的执行层实现该目标。为构建更快更便宜的存储服务。整个产品使用 Rust 和 Typescript 语言实现，最新技术架构，系统安全性和性能有保障。

### 架构设计

首先 Irys 拥有由 IrysVM 构建的执行层，故 Irys 既可以处理智能合约也可以存储数据，为了使系统具有良好的可扩展性，Irys 对区块空间设立了 3 个独立的通道 (blocklane)，分别为：代币转移、数据存储、合约调用；3 个通道上的交易类型不会互相竞争系统资源；

数据的存储采用链上存储模式，导致了相比于其他去中心化存储协议较高昂的费用。

### 数据的生命周期与可编程性

**存储**  
在存储方面，Irys 采用 Multi-ledger 架构，整体上为“缓冲区”转向“永久存储”的机制（Submit Ledger \=\> Publish Ledger）；通过该设计对数据质量和存储效率进行平衡。

数据存储相关交易中的数据首先会被提交至 Submit Ledger 中，此时数据处于等待验证的状态。  
在该状态，该数据在网络中传播，接收到数据的矿工存储该数据，对数据完整性进行校验并在对数据进行签名后继续传播，当该数据收集到足够多不同矿工的独立证明后，可以认为该数据拥有足够的健壮性，此时判定其验证完成，数据将会被发布到 Publish Ledger 上。

如果在规定的时间内该数据没有完成上述验证过程，则判定该数据在上传或网络传播过程中出现了数据损坏等情况，将不会被上传至 Publish Ledger，该分层机制的核心目的在于对数据进行筛选。  
在存储结构方面，Irys 采用三个层级的存储架构：Partition、Chunk 和 Segment，Patition 单位大小为 16 TB，Chunk 单位大小为 256 KB, Segment 单位大小为 32 Byte

**数据验证**  
Irys 引入 Matrix Packaging(MP)  技术对数据验证进行针对性优化；该技术保证数据的可验证性、可扩展性以及低成本存储。MP 技术会对每一个 Segment 生成一个哈希值，连续的哈希值构建了一个依赖结构，使得矿工必须对所有数据进行完整性校验，其效率通过 MP 中的并行处理机制进行优化，单个 Chunk 需要 40 ms 的处理时间（慢于 Arweave 的 RandomX技术），但是基于并行计算机制，同时处理多个 Chunk 时的效率较高（处理1000个 Chunk 只需要 3.5 s）；Arweave 中的 RandomX 技术以及 Filecoin 中的 zk-sealing 技术都以时间效率较低的线性序列化方式处理。

**数据查询**  
IrysVM 提供链上数据可编程性，由 Irys Gateway 持续地对链上元数据进行检索并对外提供获取数据的接口；用户可以使用 GraphQL 或者 REST API 执行定制化的数据查询请求  
执行数据查询时有两种粒度的检索单位，检索方式分别为  
chunk \<partition\_index\>:\<offset\>:\<chunk\_count\>  
byte \<index\>:\<chunk\_offset\>:\<byte\_offset\>:\<length\>

### 网络角色分工

Irys 采用 PoW 与 PoS 混合的共识机制，首先，网络中的节点或者称为矿工承担两份职责：1. 竞争记账权打包交易成区块；2. 负责存储数据。系统通过共识机制将这两项职责有机结合在一起。首先，Irys 矿工需要质押原生代币 $Irys 获得挖矿资格，其次，矿工需要对存储的数据进行完整性校验的计算，并通过该计算过程竞争记账权。在该共识机制下，存储请求的处理与数据完整性都得到了保障。当前成为矿工的要求是提供至少 16 TB 的存储资源并配备消费级显卡。

Irys 中的 PoW 也被称为 uPoW(useful PoW)，其运作机制大致为，矿工节点以本地存储的 Partition 为单位，由系统程序对存储的数据进行采样，由矿工节点对采样数据计算出密码学证明以验证其正确地存储了相关数据。

Irys 中的 PoS 机制运作方式如下：首先 Irys 矿工需要向网络提交 Stake Transaction，该交易会锁定 $IRYS 代币并激活挖矿地址；此后 Irys 矿工需要履行其存储数据的职责，如果出现数据丢失情况，将被惩罚质押代币。

**疑问：如果一个矿工退出了网络，如何处理曾经由该矿工节点负责存储的数据？**

### 存储费用定价机制

由矿工预测单个区块内存储价格，通过激励机制鼓励更准确的预测  
存储费用的确定涉及 2 部分规则（Testnet）：  
	基础费用 1MB / $0.01；起步价 $0.01  
费用调整 基于网络使用需求量对费用进行调整，具体规则如下：当前网络出块时间为 30 秒，每个区块最多处理 7500 个 Chunk，每个 Chunk 能够存储 256 KiB 的数据；当区块中超出 50% 的存储空间被使用时，往后的每个区块的基础费率开始线性增长，最多单个区块提高 12.5%，增长不设置上限 。当一个区块中没有任何 Chunk 被使用时，费用以每个区块 12.5% 的幅度下降。

### 生态合作项目

为 20 个项目提供存储服务，其中包括 AI(9个)、INFRA(8个)、CONSUMER(2)、DEFI(1个)  
![][image1]  
以 AI 相关项目为主，如 Morpheus, GOAT(Agentic finance toolkit), Infinity Ground(web3-native agentic IDE), Crynux(去中心化的EdgeAI编排器)   
Orca: DEX（创建一些小众币种的流动性池 Eclipse 的 $BITZ）  
Hey: 搭建在 Lens 上的社交网络

## 横向对比存储类项目

### 静态数据

中心化存储相比于去中心化存储可能会被诟病的问题即单点故障，但实际上互联网巨头公司都会在全球范围内构建多个数据中心以具备抗风险性，从应用的角度来说，如果去中心化方案的费用无法比拟中心化方案，加之其带来的不确定性和风险，C 端和 B 端有什么理由进行迁移？存储费用应该是分析该问题的重中之重，再谈论安全性，此处以中心化存储的费用作为 Benchmark 进行对比。  
Amazon 存储定价：$23 / TB / 月  
Google Drive 存储定价：$20 / TB / 月；每个账号默认 15 GB 免费存储空间  
DropBox 存储定价：$100 / TB / 月

| 项目名称 | 定位 | 存储架构 | 存储费用定价 | 网络角色分工 | 数据获取 | 数据完整性 |
| :---- | :---- | :---- | :---- | :---- | :---- | :---- |
| Filecoin | Layer 1 2023 年3.14 发布 FVM，支持链上计算 | 链上 \+ 链下(IPFS 系统) | 供需关系决定费用，租赁模式 $0.1/TB / 月  | 存储矿工、检索矿工 | IPFS系统支持内容寻址 | PoRep(复制证明) \+ PoSt(时空证明)用户决定存储数据的节点数量 |
| StorJ | Layer 1 | 链上 \+ 链下 | 租赁模式$1.5/TB/月且额外收取下载数据费用 $7/TB | 卫星节点、存储节点 |  | PoW \+ 声誉系统纠删码 |
| Arweave | SmartWeave智能合约协议支持链上计算 | 链上存储,分片区块链系统,网状区块结构 | 永久存储，按照 200 年存储成本计算 2.38 AR/GB\=$11649/TB | 存储节点（共同承担存储与共识） |  | SPoRA共识(涉及访问证明和工作量证明)要求所有节点存储数据备份 |
| Crust Network | Polkdot平行链 | 链下存储 | 租赁模式$0.001/TB/年 | 共识节点、存储节点、网关节点 | IPFS | GPoS,MPoW,IPFS,TEE |
| CESS | Polkdot平行链 | 链下存储 | 预言机追踪其他去中心化存储价格来定价 | 共识节点、存储节点、CDN节点、TEE节点 |  | PoIS共识 \+PoDR²质押+声誉系统+随机选择 |
| Walrus | 依赖于Sui的共识 | 链下存储 | 租赁模式 0.2WAL/GB \=$81.92/TB | 存储节点 |  | 纠删码 |
| Irys | Layer1 | 链上存储 | 永久存储$0.01/MB$10485/TB | 矿工节点(同时负责共识和存储) |  | PoS \+ uPoW |

### 动态数据 KB MB GB TB PB EB

| 项目名称 | 存储资源上限 | 已存储数据量 | 矿工数量 | 生态发展 | MC / FDV |
| :---- | :---- | :---- | :---- | :---- | :---- |
| Filecoin | 22.6 EB |  | 1480 | 基于FVM构建了关于 FIL 的 DeFi 生态 | $1.5B / $ 4.4B |
| StorJ | 30.3 PB(2023) | 18.4 PB(2023) | 20000(2023) | 项目基本处于瘫痪状态； 数据看板崩坏 | $34M / $102M |
| Arweave | 313 TB | 117 TB | 407 | Meta,Instagram, Mirror 选择其作为NFT和内容的存储方案； 数据看板：[https://viewblock.io/arweave/topStats](https://viewblock.io/arweave/topStats) 创始人进一步开发 AO 实现数据计算层 | $315M / $315M |
| Crust Network | 153 PB |  | 315 | Matters Lab 2022年投了Crust $2M;生态沉寂，项目停摆 | $2M / $ 2.5M |
| CESS | 未上线主网 |  | 尚未开放 | 2021年亚太地区Polkdot黑客松一等奖为AI计算和数据提供存储，构建AI Agent Hub;未TGE | unknown |
| Walrus | 4.16 PB | 1.1 PB | 121 nodes / 103 operators | 依赖于sui，OpenGradient (AI 平台)集成了该项目作为存储 | $531M / $1.9B |
| Irys | 280 TB | 199 GB | 尚未开放 |  | 尚未 TGE |

### 去中心化存储未来的应用方向分析

当前很多存储协议在做着相同或者类似的事情，Irys 提出所谓的”不仅仅是存储“，是早已被 Filecoin 等老牌去中心化存储赛道的先驱提出并实现了的，Filecoin 在 2023 年上线 FVM，Arweave 构建链上永久存储并支持智能合约协议，计算与存储的统一性并非当前存储赛道面临的瓶颈。

统揽全局，当前去中心化存储赛道可以按照多个标准进行分类，如数据存储位置在链上还是链下、存储计费模式采用租赁模式还是永久存储模式、是否构建单独的计算执行层。

从**生态发展的角度**来看，上述最后一种分类标准对于项目发展的影响或许是最大的，此标准下分为 2 类项目，一类是构建单独的生态，如 Filecoin、StorJ、Arweave、Irys、Crust Network、CESS Network 等，另一类是依附于已有的 Layer 1 生态的存储类项目，以 Walrus 为代表性项目（由 Mysten Labs 开发），依赖于 Sui 作为其计算执行层，**近日由 Aptos Lab 与 Jump Crypto 也宣布了 Shelby 项目的成立**，目前已经发布了白皮书，**旨在构建实时数据的热存储**，依赖于 Aptos 作为计算执行层；此外，BNB Chain 也有构建 Greenfield 作为 BSC 链的存储层，可见后者这种模式在近年逐渐引起资本的关注。

从**存储网络的构建**来看，不论是哪类存储项目，都需要构建足够充分的供需关系，以激励存储提供者和需求者，没有足够的存储需求，就无法吸引足够的存储提供者，没有足够的存储提供者，存储需求者又会对存储可靠性产生担忧，这形成了一个”先有鸡还是先有蛋“的依赖问题，这也启示着存储项目方构建技术足够可靠的基础设施是不够的；当前 Ethereum 全球范围内节点数量约为 **12480** 个(2025 年 6 月 26 日 Ethereum 官方数据)，Solana 全球范围内的节点数量为 **1083** 个(2025 年 6 月 26 日 Solana 官方数据)，这一定程度表明短期内普通的去中心化网络的健壮程度只是在数千个级别的数量级。而 Filecoin 的活跃矿工地址数为 **1480** 个。  
**缺失：分析当前去中心化存储的使用者群体主要是哪些**

从**存储位置的角度**来看，数据存储在链上还是链下这一设计，是当前诸多存储类项目构建时对架构影响极大的权衡。在存储成本上来看，链上存储数据必然导致区块空间承受着更大的压力、分布式达成共识的系统开销增加，新节点的启动成本提高，该赛道先驱项目大多采用了链上存储元数据，链下存储详细数据的设计；在应用层面带来的影响是，链上存储数据的好处在于智能合约在虚拟机中执行时，可以直接调用区块空间中存储的数据完成相关计算，**比如将 AI 模型的权重数据以及模型架构存储在链上，则可以完成 AI 模型的全链上推理（但计算开销仍然巨大，会导致极高的 Gas 费）**，而对于链下存储方案来说，由于链上虚拟机内并不能发起 HTTP 请求，这意味着无法直接利用链下数据完成相关计算操作，但合约执行时仍然可以通过 Chainlink 等虚拟机实现关键数据的获取。 结合当前存储费用来看，链上存储的价格明显过度高于链下存储方案。两种存储方案无绝对优劣之分，取决于应用场景。但 Mass Adoption 更可能发生在成本更低的链下存储方案

**简洁介绍 Irys**

**首先 Irys 提出了一种链上存储数据的新存储方案，优势在于其存储的数据可以直接被智能合约所访问，但同时带来了问题**  
**创新点1：链上存储意味着数据是永久存储的，成本很高，Irys 双账本机制过滤一部分无效数据，提高区块中有效数据的比例；**  
**创新点2：Irys 定位为存储链，但如果需要通过智能合约调用链上数据发挥链上存储的价值，该链需要承担计算的功能**

[image1]: <data:image/png;base64,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>