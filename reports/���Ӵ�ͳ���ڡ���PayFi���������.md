# 链接传统金融——PayFi网络的兴起

## **1\. 摘要**

全球金融体系正经历一场由稳定币驱动的变革。随着稳定币市场在短短5年内从约40亿美元增长至2200亿美元，我们见证了一个新兴生态系统的崛起——专为稳定币设计的区块链和支付网络。这些创新解决方案正在重新定义跨境支付、金融结算和全球价值转移的运作方式。

本报告深入分析了五个代表性项目，它们各自以不同的策略和技术架构，致力于解决全球支付领域的核心痛点：高昂的交易费用、缓慢的结算速度、有限的互操作性，以及复杂的中介结构。

**Plasma**：一个专为稳定币设计的高性能区块链，致力于提供“零手续费的 USDT 转账”，以极致优化的架构支撑下一代链上支付系统。通过对执行逻辑与共识机制的深度定制，跳过了 NFT、治理投票、空投等通用公链冗余功能，专注于一个核心目标：让稳定币流转变得极致高效、极致便宜。

**1Money Network**：一个独立的Layer 1解决方案，采用创新的"无区块"架构和确定性BFT共识，聚焦提供多种稳定币的高性能交易体验。目前得到部分传统合规机构对其认可，未来有望看到银行、支付公司直接接入1Money 网络。

**CodeX**：专注于构建企业级稳定币出入金解决方案的Layer 2网络，为机构客户提供无缝的加密与法币之间的转换服务。CodeX已完成1580万美元融资，由前Optimism、Sequoia Capital和Meta的资深人士领导，初期聚焦东南亚市场。

**Huma Finance**：定位为全球首个PayFi网络，使全球支付机构能基于稳定币与链上流动性实现全天候结算。Huma已处理超过38亿美元交易量，通过双层流动性池模型为机构投资者提供稳健回报。

**Circle Payment Network (CPN)**：由USDC发行机构Circle主导的许可型协调协议，旨在连接传统金融与区块链世界，为金融机构提供基于稳定币的合规、无摩擦的支付基础设施。CPN利用混合链上链下架构，支持跨链结算和多种稳定币资产。

这些项目共同标志着区块链技术从通用平台向专业化支付基础设施的演进，正在填补传统金融基础设施与去中心化技术之间的鸿沟，有望在未来几年内显著降低全球价值转移的成本和摩擦，为各类金融机构和最终用户带来实质性的经济效益。随着监管框架的不断完善和机构采用的逐步增加，这些项目代表的技术路线可能成为重塑全球支付格局的关键基础设施。

本篇研报的后续内容安排如下：第2节探讨稳定币市场的爆发性增长及其应用场景，同时揭示传统支付系统的核心痛点。第3节阐述从通用区块链到专业化支付网络的演变，分析三类支付基础设施及其技术与商业模式创新。第4节深入比较五个关键项目在市场定位、技术架构和商业策略上的差异化优势。第5节详细展示PayFi网络在跨境支付和B2B结算领域的具体应用场景及解决方案。第6节预测稳定币网络与传统金融的整合趋势，前瞻新兴市场和商业模式，总结未来发展的关键动向及其对全球金融体系的深远影响。

## **2\. 稳定币经济介绍**

## 2.1 稳定币市场的爆发性增长

稳定币作为连接传统金融世界与加密经济的关键桥梁，在过去五年间经历了前所未有的增长。从2019年的约40亿美元总市值，飙升至2025年初的2200亿美元，年复合增长率超过120%。这一爆发性增长使稳定币成为加密货币生态系统中增长最为迅猛的细分市场

稳定币的交易量数据更为惊人。根据CEX.io在2024年1月发布的报告，2023年稳定币的年度汇款总量达到27.6万亿美元，超过了Visa和万事达卡等传统支付巨头的处理量。2025年第一季度的数据显示这一趋势进一步加强：

![][image1]

每日与稳定币交互的 unique addresses (过去三个月)

目前 Tron 仍是稳定币转账的主要选择，过去 30 天内 Tron 上稳定币转账 total volume 为 $615.9B，转账数量为 64.7M，目前 USDT 的最大供应平台是 Tron （USDC 则主要在以太坊和 eth 二层网络发行）

* 过去30天稳定币交易量：2.93万亿美元  
* 过去30天稳定币交易笔数：6.345亿笔  
* 日均与稳定币交互的唯一地址数量持续增长

USDT仍然是稳定币转账的主要载体，过去30天在Tron网络上的交易量达到6159亿美元，交易笔数6470万笔。值得注意的是，USDT在不同区块链网络上分布广泛，而USDC则主要集中在以太坊及其二层网络上。

## 2.2 驱动稳定币采用的关键应用场景

***跨境支付与汇款：***稳定币最具革命性的应用是在跨境支付领域。传统的跨境转账系统如SWIFT，通常需要3-5个工作日完成结算，并收取高达交易金额6.65%的费用(根据世界银行2024年第二季度数据)。相比之下，基于稳定币的转账可以在几分钟内完成，费用低至交易金额的0.1%。

这一优势使稳定币成为新兴市场汇款走廊的理想解决方案。例如，在菲律宾、印度尼西亚和拉美等地区，外汇管制和高昂的转账费用长期困扰着当地居民和企业。稳定币提供了一条高效、低成本的替代渠道。

***机构结算与财资管理：***金融机构和大型企业已开始探索使用稳定币进行日常结算和财资管理。与传统银行系统相比，稳定币的全天候可用性(24/7/365)、快速最终确认和可编程性为机构带来了显著优势，

***DeFi生态系统的基础：***在去中心化金融(DeFi)生态系统中，稳定币充当核心流动性和计价单位。截至2025年初，锁定在DeFi协议中的稳定币价值超过500亿美元，为借贷、交易、合成资产和衍生品等应用提供基础。稳定币还促进了"实世界资产"(RWA)上链，创建了传统金融与去中心化网络之间的新型连接点，为资产证券化和分布式投资工具开辟了新可能。

## 2.3 传统支付基础设施的核心痛点

***系统分散与互操作性差：***现有全球支付基础设施由各自孤立的国家和地区系统构成，这些系统包括诞生于20世纪70年代的ACH等协议，以及更现代但仍受地域限制的系统，如欧元区的SEPA、巴西的PIX和印度的UPI。这些系统虽然在各自区域内运行良好，但互操作性极差，跨系统转账需要多层中介机构参与。

***高昂的支付成本：***麦肯锡报告显示，全球支付行业年收入已超过2.4万亿美元，这些收入很大程度上来自向交易双方收取的手续费，实际上成为全球商业和个人的一种"税收"。具体表现为：

* 国际电汇单笔成本高达50美元  
* 信用卡处理费通常为交易额的2-3%  
* 跨境小额汇款平均成本为6.65%(200美元基准金额)

***结算周期长与资金占用：***

传统银行系统的结算周期漫长：

* 国内转账：1-3个工作日  
* 国际转账：3-10个工作日  
* 信用卡结算：30-45天

这些延迟导致大量资金被"搁置"在传输途中，给企业带来额外的流动性压力。对进口商和买家而言，不得不等待数天完成对外支付；对出口商和卖家而言，不可预测的结算窗口意味着更高的运营资金需求。

***有限的可编程性：***传统金融基础设施缺乏内在的可编程性，难以支持复杂的业务逻辑和自动化流程。这限制了支付与其他业务流程的无缝集成，增加了运营复杂性和错误风险。

## **3\. 专业化支付基础设施的兴起**

**从通用区块链到支付优化网络的演变：**

区块链技术的发展经历了几个显著的阶段。第一代区块链(如比特币)专注于价值存储和转移的基本功能；第二代区块链(如以太坊)引入了图灵完备的智能合约，开创了去中心化应用的广阔可能性；第三代区块链则着重解决可扩展性和互操作性挑战。

然而，这些通用型区块链平台在支付场景中表现出一系列局限性：

* **高昂的交易费用**：以太坊上的稳定币交易在网络拥堵时费用可高达数十美元，即使是Layer 2解决方案也难以降至零费用水平  
* **交易确认延迟**：许多区块链需要多个区块确认才能保证交易最终性，导致结算体验不佳  
* **用户体验复杂**：用户通常需要持有原生代币(如ETH)支付Gas费，增加了使用门槛  
* **功能冗余**：通用型区块链包含大量与支付无关的功能，增加了系统复杂性和攻击面

针对这些问题，我们正见证着一个新趋势的兴起：专为稳定币交易和支付场景定制的专业化基础设施。这些专用解决方案通过聚焦特定用例，实现了性能、成本和用户体验的显著优化。

***专业化支付基础设施分类：***

1. 零费用稳定币区块链(Plasma, 1Money)  
   这类项目构建了完全专注于稳定币转账的高性能区块链，通过深度技术优化实现零或近零的交易费用。它们通常具有以下特点：  
* **极度精简的链上功能**：仅保留支付和基本资产转移功能，放弃NFT、链上治理等复杂功能  
* **高效共识机制**：采用专为高频小额交易优化的共识算法  
* **交易费用补贴模型**：采用网络补贴或其他创新机制消除终端用户的手续费  
* **面向零售用户**：主要面向个人用户和小型商户的日常支付需求  
  零费用区块链特别适用于对成本敏感的高频小额支付场景，如日常消费、小额汇款和内容创作者打赏等。例如，Plasma宣称"零手续费的Tether转账"，通过定制的共识机制和EVM兼容性，实现了稳定币交易的极致优化；而1Money Network则采用创新的"无区块"架构，每笔交易实时达成共识并结算，无需等待打包出块。  
    
2. 机构支付网络(Huma Finance, Circle Payment Network,)  
   这类项目构建了连接传统金融体系与区块链世界的专业支付网络，主要服务于金融机构和大型企业客户。它们通常具有以下特点：  
* **许可型网络架构**：参与者需通过身份验证和合规审查  
* **完善的风险管理框架**：包括分层结构、首损覆盖和流动性保障机制  
* **合规优先设计**：内建AML/KYC流程和跨境监管合规能力  
* **与传统金融系统的互操作性**：支持法币入金出金和跨系统结算  
* **复杂的支付路由**：优化支付路径和货币兑换效率  
  机构支付网络特别适用于大额跨境支付、企业财资管理和机构间结算场景。例如，Circle Payment Network(CPN)定位为"金融机构导向的设计"，通过与全球银行、支付服务提供商合作，提供合规、无缝且可编程的框架；而Huma Finance则定位为全球首个PayFi网络，为普通投资者和机构投资者提供基于稳定币与链上流动性的全天候结算服务，已处理超过38亿美元的交易量。  
3. 出入金便利工具(CodeX)  
   这类项目专注于解决加密货币与法定货币之间的高效转换，填补了链上世界与传统金融之间的空白。它们通常具有以下特点：  
* **多币种支持**：连接多种稳定币和法定货币  
* **API优先设计**：提供企业级集成能力和定制化服务  
* **跨境支付优化**：针对特定市场和支付走廊提供优化解决方案  
* **合规义务外包**：为企业客户提供合规流程的外包服务  
  出入金便利工具特别适用于加密支付服务提供商、跨境电商平台和需要跨境支付的企业。例如，CodeX专注于构建企业级稳定币出入金解决方案，为机构客户提供无缝的加密与法币之间的转换服务，初期聚焦东南亚市场的高额跨境资金流转需求。

***技术与商业模式的创新融合：***

这些专业化支付基础设施项目不仅体现了技术创新，更反映了商业模式与技术架构的深度融合。我们观察到以下几个关键特点：

1. ### 针对性能和成本的精确权衡

   与试图解决所有问题的通用型区块链不同，专业化支付基础设施在设计时会针对特定使用场景做出精确的权衡。例如：  
* Plasma牺牲了部分去中心化程度，通过定制共识实现极致转账效率  
* CPN采用混合链上链下架构，结合了中心化系统的性能与区块链的透明性  
* Huma Finance的分层资金池模型为不同风险偏好的投资者提供差异化回报

2. ### 商业模型与技术架构的一致性

   这些项目的技术设计直接服务于其商业目标与目标用户群体：  
* 面向零售用户的零费用区块链(如Plasma)优先考虑易用性和最小摩擦  
* 面向机构的支付网络(如CPN和Huma)则优先考虑合规与风险管理  
* 专注企业服务的出入金解决方案(如CodeX)则优先考虑API集成与定制化能力

3. ### 多方参与的生态系统设计

   这些专业化支付基础设施通常设计了多方参与的生态系统，明确定义了各参与方的权责和激励：  
* Circle Payment Network明确区分了OFI(发起金融机构)、BFI(接收金融机构)、终端用户和服务提供商的角色与权责  
* Huma Finance设计了完善的角色体系，包括协议所有者、资金池所有者、评估代理(EA)、贷款人和借款人等  
* 1Money Network和Plasma则通过区分验证节点运营商与普通用户，平衡了去中心化与性能之间的矛盾

## ***专业化趋势的市场意义：***

专业化支付基础设施的兴起代表着区块链行业从技术驱动向应用驱动的转变，标志着加密货币生态正在回归中本聪最初设想的"点对点电子现金系统"愿景。这一趋势有望加速稳定币在主流金融体系中的应用，推动区块链技术从投机领域走向实用价值。

随着这些项目的成熟和市场验证，我们可能会看到未来几年内稳定币支付网络处理的交易量大幅增长，成为全球支付基础设施的重要组成部分。这不仅将为加密行业带来实质性的价值捕获机会，也将为全球金融体系的效率与包容性带来根本性提升。

## **4\. 关键项目比较分析**

## ***项目概览与市场定位：***

| 项目 | 核心价值主张 | 技术特点 | 目标用户 | 融资规模 | 主要支持方 |
| :---- | :---- | :---- | :---- | :---- | :---- |
| Huma Finance | 解决跨境支付垫资问题的PayFi网络 | 结构化金融框架,资产通证化 | 机构投资者,支付公司 | 约4630万美元 | Solana, Circle, Stellar |
| Circle Payment Network | 金融机构间稳定币协调协议 | 混合链上链下架构,OFI-BFI网络 | 金融机构,企业客户 | Circle融资支持 | Circle生态系统 |
| CodeX | 企业级出入金解决方案 | Layer 2,企业级API | 企业,机构投资者 | 种子轮1580万美元 | Dragonfly, Coinbase, Circle |
| Plasma | 零手续费稳定币转账 | 比特币侧链,EVM兼容 | 个人用户,DeFi参与者 | 约2750万美元 | Bitfinex, Tether, Framework |
| 1Money Network | 高性能稳定币专用网络 | "无区块"架构,DBFT共识 | 日常支付用户 | 种子轮2000万美元 | Kraken, KuCoin, BitGo |

## ***项目技术架构比较：***

不同项目采用了截然不同的技术架构，反映了其在性能、安全性、兼容性和合规性之间的不同权衡：

1. 区块链设计与共识机制  
* **Plasma**：比特币侧链设计，自研BFT共识，链上状态定期锚定到比特币网络  
* **1Money Network**：独立Layer 1，采用"无区块"架构和确定性BFT共识，实现秒级确认  
* **CodeX**：基于OP Stack的Layer 2解决方案，继承以太坊的安全性和乐观卷叠的扩展性  
* **Huma Finance**：构建在Solana等现有公链上的应用层协议，利用底层链的高性能  
* **CPN**：混合链上链下协议，不依赖特定区块链，支持多链稳定币跨链转移  
2. 智能合约支持与功能范围  
* **Plasma**：完全EVM兼容，支持复杂DeFi协议部署  
* **1Money Network**：有意放弃图灵完备性，专注基本支付功能，提高安全性  
* **CodeX**：支持EVM智能合约，但主要功能通过API提供  
* **Huma Finance**：实现复杂的结构化金融框架，包括分层、首损覆盖和收益管理  
* **CPN**：计划从链下API逐步过渡到智能合约协议架构  
3. 安全模型与合规框架

| 项目 | 合规措施 | 机构整合程度 | 协议/系统特殊安全设计 |
| :---- | :---- | :---- | :---- |
| Huma Finance | 分层合规框架，Huma Institutional 有KYC要求 | 高 | 首损覆盖机制保护投资者 |
| Circle Payment Network | 完整KYC/AML流程 | 极高 | 资格凭证系统确保可信参与 |
| CodeX | 完整KYC/AML流程 | 中高 | Layer 2继承以太坊安全性 |
| Plasma | 合规主要依赖稳定币发行方（例如 Tether 可对涉嫌违规地址执行黑名单冻结）和外围监管。Plasma 更强调去信任化和抗审查性，而非主动合规。 | 低 | 比特币锚定提供最终安全保障 |
| 1Money Network | 完整KYC/AML流程，链上集成制裁名单 | 中 | 简化架构降低攻击面 |

4. 业务模式和价值捕获  
   各项目采用了不同的商业策略和收入模式，针对不同市场段进行优化：

| 项目 | 费用结构与收入来源 | 激励机制设计 |
| :---- | :---- | :---- |
| Huma Finance | 服务费、协议费用和交易费的综合收费结构 | 设计了Feathers系统，通过多种乘数机制(锁定期、忠诚度、社区助力等)提高LP收益 |
| Circle Payment Network | 支付费用、外汇点差和网络费用的分层收费模型 | 为PFI设计了多层激励，包括交易处理费、外汇兑换费和增值服务收入 |
| CodeX | 交易费用、外汇点差和企业服务费三位一体的收入模型 | 专注API集成和定制化服务，通过降低企业集成门槛促进采用 |
| Plasma | 交易零手续费，通过生态系统DeFi协议产生的间接收益获利 | 为早期DeFi协议提供激励，如Aave V3部署将获得千万美元级激励支持 |
| 1Money Network | 低廉固定手续费模型，以稳定币计价 | 计划通过合作伙伴补贴实现部分场景"Gas全免"体验 |

5. 发展阶段和市场表现  
   

| 项目 | 产品阶段 | 主要目标用户 | 次要目标用户 |
| :---- | :---- | :---- | :---- |
| Huma Finance | 已上线Huma 2.0和Huma Institutional  | 机构投资者、支付公司 | 零售投资者(通过Huma 2.0) |
| Circle Payment Network | 链上链下混合系统 | 银行、金融机构 | 企业客户 |
| CodeX | 菲律宾地区服务已上线 | 跨境企业、机构 | 支付服务提供商 |
| Plasma | 未上线 | 个人用户、DeFi参与者 | 交易所、收款商户 |
| 1 Money Network | 未上线 | 个人用户、小型商户 | 内容创作者、汇款用户 |

## ***稳定币支付网络的差异化竞争策略***

这些专业化支付基础设施采用了不同的竞争策略，以在快速发展的市场中建立差异化优势：

* 垂直整合战略部分项目采用了垂直整合策略，打造完整的支付解决方案：  
  * Circle同时作为USDC稳定币发行方和CPN网络的主要治理机构，实现了从资产到基础设施的垂直整合  
  * Plasma与Tether(USDT)的密切合作，获得了包括Paolo Ardoino(Tether CEO)在内的战略投资  
* 地域聚焦战略一些项目选择首先专注于特定地区市场：  
  * CodeX初期聚焦菲律宾市场，瞄准"东南亚地区存在数十亿美元的月度资金流动"的机会  
* 技术卓越战略还有项目则以技术优势为核心竞争力：  
  * 1Money Network采用创新的"无区块"架构和确定性BFT共识，宣称TPS可达25万  
  * Plasma通过比特币锚定技术提供安全保障，结合EVM兼容性，为DeFi协议迁移提供便利

## **5\. 市场应用和使用场景**

***跨境支付和汇款：***

跨境支付和汇款是PayFi网络最具革命性的应用领域，能有效解决传统系统中的痛点。各专业化支付网络针对跨境支付场景提供了创新解决方案：

**Huma Finance的垫资模型**:

* 通过资金池为支付公司提供垫资服务，实现"即时到账"  
* 将各支付公司分散进行的垫资集中化，提高资本效率  
* 已处理超过38亿美元交易量，证明了模式可行性

  **CPN的OFI-BFI协调框架**:

* 发起金融机构(OFI)与接收金融机构(BFI)直接协调，减少中间环节  
* 支持法币→稳定币→法币的完整流程，无缝对接传统银行系统  
* 为接收方提供保留稳定币或转换为当地货币的选择灵活性

  **CodeX的区域市场策略**:

* 专注东南亚等有大量资金流动的新兴市场  
* 提供企业级API，方便跨境企业集成支付功能  
* 通过Quote-based off-ramp交易实现稳定币到法币的高效兑换  
  典型应用场景：  
  	**中小企业贸易融资**:  
* Huma Finance的应收账款保理服务为中小出口商提供流动性  
* 解决传统贸易融资中小企业准入门槛高的问题  
* 通过链上透明性提高贸易双方信任，降低融资成本

  **菲律宾侨汇通道**:

* 菲律宾人口约1.1亿，每年超300亿美元的外劳侨汇. 汇入国内。居民消费意愿强烈，私人消费占GDP比重约73%，传统渠道费用高达7-10%  
* CodeX在此市场提供法币到稳定币的无缝转换，将成本降至1-2%  
* 实现24/7全天候到账，解决周末和假日无法转账的问题

***B2B支付解决方案：***

企业间支付是另一个具有巨大潜力的应用领域，尤其适合机构支付网络。稳定币支付网络为B2B场景带来显著优势：

	**提升现金流管理**:

* Huma Finance的应收账款支持的信贷额度使企业能更灵活管理现金流  
* 循环信贷额度为企业提供低成本、高效率的短期融资

  **降低营运资本需求**:

* 近实时结算减少了企业对短期融资的依赖  
* CPN为进口商和出口商提供的快速结算服务缩短了现金转换周期

  **自动化对账与结算**:

* 链上交易的可审计性和透明度大幅简化对账流程  
* 智能合约可实现条件触发支付，减少人工干预

## **6\. 未来展望和预测**

***与传统金融基础设施的整合：***

稳定币支付网络与传统金融体系的融合将是未来发展的关键趋势。

1. 与传统银行系统的整合  
   **API桥接模式**:  
* 银行核心系统通过标准化API与稳定币网络连接  
* 银行客户无需改变使用习惯即可享受稳定币转账优势  
* 类似于CodeX的企业API，但扩展至更多银行系统  
  **托管银行模式**:  
* 专业托管银行为稳定币网络提供法币入口和出口  
* 构建合规保障，解决银行对加密资产的犹豫  
  **银行作为验证节点**:  
* 传统银行直接参与稳定币网络运营，成为CPN中的PFI或1Money Network的验证节点  
* 增强网络可信度，同时降低银行自身的技术研发成本  
2. 与支付处理商系统的整合  
   全球支付处理商（如Stripe、Adyen、WorldPay）与稳定币网络整合的模式：  
   **后端替代战略**:  
* 支付处理商在后端使用稳定币网络处理跨境结算  
* 商户体验保持不变，但成本和速度优化  
  **可选支付方式**:  
* 将稳定币支付作为传统支付方式的补充选项  
* 商户可根据特定场景选择最优支付渠道  
  **全栈整合**:  
* 支付处理商可能收购或深度整合稳定币网络  
* 构建新一代支付基础设施，兼具传统渠道便利性和稳定币效率

***新兴市场与使用场景预测：***

稳定币支付网络将催生新的市场应用和商业模式。

1. 创作者经济基础设施  
   * 微赞助模式：粉丝可向创作者发送小至几美分的赞助  
   * 内容即服务：按秒计费的内容消费模式，替代订阅制，创作者获得更精准的内容价值反馈  
2. 新型跨境商业模式  
   * 去中介化全球供应链：中小企业直接对接全球供应商，实时付款降低交易摩擦，提高供应链效率  
   * 全球即服务人力市场：远程工作者可无障碍接收全球任何地区付款，消除传统薪资支付的地域限制  
   * 微型跨境企业崛起：降低国际支付门槛推动超小型企业全球化，个人企业家可高效参与全球贸易

***总结：***

稳定币支付网络正处于从早期创新走向主流应用的关键转折点。未来发展将呈现以下关键趋势：

1. **传统金融与加密创新融合**：不再是对立替代关系，而是互补增强，共同构建下一代全球支付基础设施  
2. **监管清晰化与合规成本降低**：随监管框架成熟，合规将从障碍转变为竞争优势  
3. **技术协同与标准化**：底层技术栈趋同，差异化将主要体现在应用场景和用户体验  
4. **新商业模式爆发**：跨境创作者经济、微服务计费、机器对机器支付等创新商业模式加速涌现  
5. **地缘政治因素影响**：多元化稳定币生态系统与区域性支付网络并存发展

## 已跟踪的五个项目各具发展潜力：Plasma和1Money Network可能在零售支付领域建立优势；Huma Finance和CPN有望成为机构间结算的重要基础设施；CodeX等区域专注型解决方案将继续填补特定市场空白。

最终，稳定币支付网络有望实现中本聪比特币白皮书最初设想的"点对点电子现金系统"愿景，但以一种与现代金融体系更加整合、更具普遍适用性的形式出现。这种演变将为全球贸易、创新和金融包容性带来深远影响。  


[image1]: <data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAloAAAEvCAYAAACdXG8FAAA570lEQVR4Xu3diZcUVZY/8PnTXAAZbTfaBQoUWhSkQRmwcMEWKRBpGDlCo8gqI0LL0o2gwAiIgjTtBm6g9IgICA2IyNrsy/v97pvzYl5+K6J875KZXKzv55zvyciXka9uLRlxKzIy89/+7f/7n//5H8cwDMMwDMPUL9JjeXKFiIiIiOqDjRYRERFRg7DRIiIiImoQNlpEREREDcJGi4iIiKhB2GgRERERNQgbLSIiIqIGSW603nvvPffggw8WGThwoB8fOXKk69WrlxszZkzN+t9//71raWlxvXv3dgcOHKgcC8rmicdwfSIiIiLrkhut1atXu3HjxvlI8yN56qmn/OWCBQv85YQJE/y6YXzo0KFuwIABfvny5cvtxoKyeXAsXp+IiIjoWpDcaMWk6enTp09NA1S2vH37drdp0ya/vHv37nZjx44dq7xv2VhYn4iIiOhakN1oLVmyxDc9e/fu9ZdDhgzx4/J0IDZGgSyvWLGi3Zg0XGEZ5ykbC+sTERERXQuyGq3FixeXHmmqWt65c6fbvHlzsYxjR44cqbxv2VhYn4iIiOhakNVohYZn48aN/vqWLVtqmiJposrG5WnG+P7xWNn6Mg+OxeunkO+FYRiGYRim3skh6yc3WuLw4cM45LZt24ZD3qFDh9odhSobC8rmKRsjIiIiuhZkN1pERERElIaNFhEREVGDsNEiIiIiahA2WkREREQNwkaLiIiIqEHYaBERERE1CBstIiIiogZho0VERETUIGy0iIiIiBqEjRYRERFRg7DRIiIiImoQNlpEREREDcJGi4iIiKhB2GgRERERNUina7SmTJnibr75Zjds2DB3yy23+LHrrrvOtbS0+Evx4Ycfuq5du7obb7yxGIstX768ZvzNN9/010eMGFEzjtdR7969i9tlju7du7tevXq58ePHw5pERER0Lep0jZY0NmfPnvXL586d85ezZ8/2l926dXNHjx51mzdvdidPnnQ7d+4sxmIyx+23315c79mzp19P9OvXz8975swZ16NHjw4bLbkt3C5zHDt2zF24cMHdcMMNRW1ERER07epUjdbFixf9UaZ9+/b5IGl2sKkqGxP33XdfsTxq1CjfMJ0/f75dY4XXg7a2Nnfo0KHidplj2rRpbtGiRW7cuHGw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>