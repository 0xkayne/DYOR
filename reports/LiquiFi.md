# LiquiFi

## 公司背景

LiquiFi 成立于 2021 年，由 Robin Ji 和 Oliver Tang 在旧金山共同创立。2022 年通过 Y Combinator 加速器，同年完成由 Dragonfly Capital Partners 领投的 500 万美元种子轮融资。 2025 年 7 月 2 日，Coinbase 宣布收购代币管理平台 LiquiFi，Coinbase机构产品副总裁Greg Tusar表示："收购LiquiFi使我们获得了代币cap table管理、归属权和合规方面的最佳能力，并使Coinbase能够在构建者的早期阶段为他们提供支持。" Coinbase 会将 LiquiFi 的功能深度整合到 Coinbase Prime 平台。这是其 2025 年第四次收购(并购推文 [https://x.com/liquifi\_finance/status/1940400092453699681](https://x.com/liquifi_finance/status/1940400092453699681))。Coinbase 今年前三次并购项目为Spindl（广告）、Iron Fish团队（隐私）、Roam.xyz 团队（搜索）

LiquiFi 的目标是做成“加密货币领域的Carta”，专注于自动化代币分发和合规解决方案，目前服务于 Uniswap Foundation、Optimism、0x(DEX聚合器)、Ethena等头部项目。

融资情况：

| 时间 | 金额 | 估值 | 轮次 | VC |
| :---- | :---- | :---- | :---- | :---- |
| 2025 年 7 月 | unknown | unknown | 并购 | Coinbase |
| 2022 年 4 月 | $ 5 M | unknown | 种子轮 | Dragonfly 领投,Nascent, Alliance DAO, 6th Man Ventures, Robot Ventures, Y Combinator, Orange DAO, Balaji, Katie Haun, Packy McCormick, Anthony "Pomp" Pompliano, Anthony Sassano参投 |

团队成员：

| 人物 | 职位 | 履历 | 推特账号 | LinkedIn账号 | 特殊情况 |
| :---- | :---- | :---- | :---- | :---- | :---- |
| Robin D. Ji | Co-founder, CEO | 加州大学洛杉矶分校毕业, 2021年开始做LiquiFi | @robindavidji 3k粉 | https://www.linkedin.com/in/robindji/ |  |
| Oliver Tang | Co-founder, CTO | 密西根大学毕业，2018 \-2021 在Amazon 任工程经理，2021年开始做LiquiFi | @olivertang\_  | https://www.linkedin.com/in/oliver-q-tang/ |  |

Robin D. Ji 曾在摩根士丹利和Jefferies担任投资银行分析师，后在Adobe、LinkedIn等知名公司从事产品管理工作；CTO Oliver Tang则拥有Amazon、Salesforce等大型科技公司的工程管理经验。

## 社媒数据

| X粉丝数 | Discord粉丝数 | 其他媒体 |
| :---- | :---- | :---- |
| 3.2K |  |  |
|  |  |  |

## 产品

### 核心业务

LiquiFi 的***核心定位***是"加密货币的 Carta "，专注于解决 Crypto 公司在代币管理方面的痛点。明确采用 B2B 策略，专注于服务已发布代币或准备发布代币的加密货币公司。其业务涉及代币生命周期中的一些关键环节：代币归属和锁仓管理、全球税务合规、空投和代币分发、企业级服务；

代币归属 (Token Vesting) 和锁定管理 (Token Lockup) 是 LiquiFi 的核心，Token Vesting 市值按照代币预设的时间表和条件逐步释放给持有者的过程，如最常见的线性释放(Linear Vesting)，LiquiFi 平台提供自动化的代币归属管理时间表，支持复杂的归属和锁仓组合设置；技术方面，LiquiFi 采用混合托管模式，平台将智能合约设置为可选项，尽管智能合约有诸多好处，但是也存在合约漏洞等风险；在用户侧，系统集成了Safe 多签钱包，提供分布式控制和安全性保障，并支持用户自定义归属时间表，提供模板化设置，以处理复杂的归属安排。  
![][image1]

同时，平台提供实时代币税务预扣计算，针对不同国家配置相应税率，自动化处理税务合规流程，集成了 KPMG（国际四大会计师事务所之一） 国际税务引擎，可以为任何国家的员工计算税务预扣，在监管环境日趋严格背景下帮助 Crypto 公司解决运营中的税务合规挑战；

在空投和代币分发自动化，LiquiFi 支持各种钱包类型和自定义分发逻辑，确保分发过程的灵活性和安全性，平台已经证明能过够处理超过 5M 接收地址的大规模空投活动。Renzo Protocol 通过 LiquiFi 平台成功向 100K 地址分发了超过价值 $275M 的代币。 

在企业级服务方面，与 Deel （全球人力资源科技公司）合作，提供代币和法币混合薪酬管理， 以及与受监管的 OTC 合作伙伴为机构客户提供大额交易服务。这些服务帮助Web3公司实现传统企业级的运营标准。

***完整业务流程：***  
预启动阶段，项目方编写代币文档和法律框架，配置员工代币奖励和投资者认股权证，设定股权表管理和分配规划；之后进入启动阶段，通过平台支持 TGE 事件、自动化分发代币，并得到合规与监管方面的指导；最后进入启动后的运营阶段，客户通过平台进行持续的归属和锁定管理，税务预扣自动化，持续合规监控。

***商业模式和定价策略上：***  
LiquiFi 采用 Saas 订阅模式，起价为 **$900 / 月**，设定 Starter、Growth、Scale、Enterprise四个层级，不收取额外交易费用

### 技术分析

智能合约安全性方面，LiquiFi 平台的智能合约通过 CertiK 等多家合约安全公司审计，并获得了 Sherlock 提供的 1000 万美元智能合约保险。

当前 LiquiFi 支持包括 Ethereum、Polygon、Arbitrum、Optimism、BNB Chain、Avalanche、Ronin、EON、Scroll 等在内的多个区块链网络。目前专注于 EVM 兼容链，提供统一界面管理跨链代币。 LiquiFi 计划扩展至 Solana、Cosmos、Celo等非EVM链。

API 采用 Serverless 架构构建，可部署到 AWS 等云服务厂商，核心 API 由 Typescript 编写，提供标准 REST API 与 SDK 和开发者工具，支持自定义集成。

## 同赛道竞品

| 项目名称 | 业务 |
| :---- | :---- |
| Hedgey | 提供免费的 on-chain token vesting 解决方案 |
| Sablier | 目前比较成熟的vesting平台运营 5 年零安全事故 |
| Magna | 获得 1500 万美元融资定位为" Web3 的 Carta" |
| TokenSoft | 处理超过 10 亿美元资产 |

LiquiFi 的竞争优势体现在**综合服务能力**：不仅提供基础的 vesting 功能，还整合了税务合规、空投管理、OTC 交易等全链条服务。Coinbase 的收购也为平台带来了强大的资源支持和生态整合能力。

赛道前景：Crypto 代币管理市场 2024 年规模约 **$2B** ，预计 2030 年将达到 **$2.5B**，年复合增长率达到 **23-25%**，这为代币管理服务提供了广阔的市场基础。（数据来源于机构ResearchAndMarkets的研报：[https://www.globenewswire.com/news-release/2025/06/27/3106387/28124/en/Crypto-Asset-Management-Market-Trends-and-Investment-Opportunities-2025-2030-Growth-in-DeFi-and-Tokenization-Drives-Demand-for-Crypto-Asset-Management-Tools-in-Decentralized-Market.html](https://www.globenewswire.com/news-release/2025/06/27/3106387/28124/en/Crypto-Asset-Management-Market-Trends-and-Investment-Opportunities-2025-2030-Growth-in-DeFi-and-Tokenization-Drives-Demand-for-Crypto-Asset-Management-Tools-in-Decentralized-Market.html)）

[image1]: <data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAYMAAADICAIAAACF7hpeAAAYx0lEQVR4Xu2d3YtUV7rG5z+p64BezE0T9DItwauxL4IXh05AThPsMeAoKjokYCckHA9EQsJMwDFg5ohCJwbGHojBDM2B9BCIcyHjdEwOEfI1HXBiqh3Ljh+9z1P76Xp9e62qctdH1+qq/Tz82Kxae621d717rWevXXvZ/qL286oQQiTk5q3bv4hzhRBikMiJhBDpkRMJIdIjJxJCpEdOJIRIj5xICJEeOZEQIj1yIiFEeuREQoj0yImEEOmREwkh0iMnEkKkR04khEiPnEgIkR45kRAiPXIiIUR65ERDz7anJpj48sZ3lvP0rkmmn5nca2Wwffud89jaR2tkz/RhwEZ8AbD/yAwTlmmNWy07Lg8Hrly9vmVsh+Vbdcux9Ik3Tlkt5LPBF1856Y/IvZUnnjw7O1erf6lp5uDcsMX52CmJIUVONPRgfDJBJ+JYBfOffFZrDGOWwRbDnvm+IsqgLtgyNo4tygQFLOGbQjso+acP569c/TzYFWyDFvzHt985x8MxB2eCZukvZje+qad3PYsCKMaPsDArJoYaOdHQY6OaTmQzET8bssGMYY9JB4d6bBNIoBHML6wAEjAaJiwTYMrDIyK9dHPZqsOY8r2fe3/xCbYT59sZWk5TJ8rz9/JL2WQK3mR7xZAiJxp6KvkzC0YjnQi+EAx1jFgbzE3nRLAPjG1Y2NnZi63mRDgEZ1uVfDYEC+DchLMYX8yOhSdB3wITwUecLdIwHT6U+ae2wIny01tr3OyVcyJ8XzzN+fbF0CEnGlngL3GmEJsTOZEQIj1yIiFEeuREQoj0yImEEOmREwkh0iMnEkKkR04khEiPnEgIkR45kRAiPXIiIUR65ERCiPTIiYQQ6ZETCSHSIycSQqRHTiSESI+cSAiRHjmRECI9ciIhRHrkRKVjx29r2G47UN/+auYu0wuLD5DYlX8kXy09ZAJ7WYAJVgTvL9zzOX6Xte+3735cL8+9PJztquWHZgtBs6IkyIlKB0b482/Vhz3SP1TrOc+/ufaxlRNZpi9A6CmX/nafH2lz4MR7P7MuLYzp8WPtnMja9PmiJMiJSgfsAOMcM5SX/rhSy6c2nI/UenAitBYXZiZy6FNIoDq9T04kAuREpeOHnx5NWGxL37FHJOb7RPz4RrynBPbh248zg4Q/dFxLjDxyIiFEeuREQoj0yImEEOmREwkh0iMnEkKkR04khEiPnEgIkR45kRAiPXIiIUR65ERCiPTIicrFM5PTTGx7aiLeC87OXtx/ZAZUnniSOVeufh4XI1amOP64V65ex/bLG9+9+MrJuKQoFWmcaPnu6s1/r957kJWWH2ur/7oThmUAmBPRRLD9/Tvn8vy9J944hcT8J58hk+AjMp/e9Sy2W8Z2YAuHQnk4CNtBmf1HXmbCLMbqoool/F4cAtV5OHgQ2kezPDcUw5aNYwsTfHrX5J7pw6w7GNAzV+6H16s84LsjAnFYNpo0TnR7ZTUrvVZXszgy/WLHzA+//M0/4/zAiVz+Iyeia1gB5HAXTAemgHx4hzWydHO5Vp9JzXmvsTkO6vqjcC8zrX3MiehEaNYaMUvC3uBUNxQMwvA6lVKDv02mcaKHuty54sj0hf9bug8bIsEuzjsAhzcSmLDUcl/A7KPWzIls/oIc+gINgjmcE9GhWJ4TKKZpOphGsXFWCZwIdelEZjooAIPDR54njzUY5ETU4KdFcqKUiiPTF2BAmBMxsf3YUlzAM8hxvvmRE1FyonIpjkzvnF+4Y1OhyTdvxtMi0QY5ESUnKpfiyPQOrAdPZ/5jXEa0Qk5EyYnKpTgyvQPr+d/FFf8xLiNaISei5ETlUhyZ3nn9z8vmPtuOLnXnRGdn5+JMgz8w9xH/Hq1p/sCQE1FyoqKa/WCukq9bCXd0rq1jO5g4eGxm/Z4NVxyZvmAvzlrZkB/h8598Zs7y4isnl25Wa7kT2cs1WzpkVVj+7OxF36bfdeXq5yxvr8N8Yb74rzXaxEEDJ+LLO54DX9sNjN6d6ORbpxY+vYIEO6fvokwfOLqumw2+1xWRnKioeFGvLV7H9ptvv/dXnVtaVbW6nG9vM//rb79n9WuLX1hh6ytIoBsFJZmz+7np7eMTVv74ayd9+a4VR2YwVPKRzy2cyM+AvAswx5YgmSnQbsxQCCwMdblO8uKH86xuTtT0DR2P9czkXjsWi7F9OpStMIrZMjYeZ/ZI706U1e9t41MvHGK/Qpqd8OtGL6UTIY0uyoR1ts2jsjsRx3lMWC7Xpcv17p45A/IfzVNYGIndz9V7vH20rfWDoLUsny6hG+EWh7rg+Kv1scG9yKz03IfiyAwAWI/5AuyDBGWYw4U/ttcX4z/U4JbYIsZgNaM/FqvE7Xif8odmPrYgOMl4zWRf6IsTsSuih9h8h32PnQdOxN7Iybj1yU2lsjtRUzW9VMy0eQq3/qN3IusEsxfqdyGfn7V1Iiaqy7fZmt3WKnk/88W6UxwZkZa+OBEmRAcbEx+/ZQJORA8KbpabSnKiJuKYH0nFkRFp6YsTjYDkRGviTz829RhVxZERaZETUXKiNWFye+nyPPwID1yb8+VCXxRHRqSllRNVq8t4mArgT84jKTnRI9lz9QgrjoxISysnatoV+WPQSEpO1ERNO8FoKI6MSIuciCq7E8UTYNC0EzBz69h4uGO9vin8ln3h0yuYgV9b/CLc0Vbx64/dz00/2p2/vvUfA8WREWkp4kSt0gXVvkt0py5Oo73K7kTZ+oeyNg9oOyeevXR5Pmu8mD/+6knmbx+fMPepLq8taKwX+2DO3vEzHx3CP+fH3QvexCpZ3iwPl+XuZoeoNJYUWUk60UeX55mwBdxN9dXSQ7F5WFh8UNCJcHGZ07R/oksES0MsgVuXdTz0Gd7JZi9cZAKa2ncYH5k2oeTpM+eYtlsduhZGAdPWOD9ab+xacqKisuU8vBh2n/HmQr/gRUIxXh67olyvaIXtonLJYpY3xaOwHa6rpqwRCuVtdhbMido7URwZkZALC/cKOlHTdFMFToR+EqxpPH3mvCue8d8DBLJejbrok/ynBSZUCU6j95/S5URFZf/CAxMcJP7z14eYj+vkBz8vEkvSI1CxlTvAjFiGnoV5DSZcrHvw6IxZDPbunJhk+mC+XpYvVqxklh/LN9VKcWREWgo6kdH0+iLTz6aZsH7IvmoNsgDuc8xBR2Lv8kf8qDEfP/nm2qwHe3E7tFGABB4LDjbWTKJ8j8tf5ET9l01ZN6HiyIi0FHEiU0e/WDfth3/tzS82TnKicimOjEhLKyfCzMVPhYyw3KhITlQuxZERaWnlRGWTnKhciiMj0iInouRE5VIcGZGWgTnRpcvz/pejqRfWXrl0Kv/LdB//XZScqFyKIyPS0hcn2jkxuTNfFAKbWFsx9MEcE6fPnLNXt3zX/s2330/tO2yuhL0Hj85Uq8v86H+KqjSWwqE828/cqjdbfdIXlcWJ7t4Pv3k5FUdGpKUvTmTyr/Oz/E+M+hy/6scW62OvfyUX/CMB1oVb2ZoSOhHwfwiwd5XFiX6slf0/pL6b6H8fF+3pixPBVmgZ8fu1Sr4+m2n767FwFjpRbijT5kTBhChrLCyquD9bDCeyZUTHXzvZ4zIi0+A7ZxonIssr5SWOhtgM9MWJ+qWmS5AGo3I5kRCbjU3lRAklJxIiJXIiSk4kRErkRJScSIiUyIkoOZEQKZETUXIiIVIiJ6LkREKk5M7PcqLsVi0MywCQEwkR8lNt9VZZ+SmFDdXkREKIzYCcSAiRHjmRECI9ciIhRHrkREKI9MiJhBDpkRMJIdIjJxJCpEdOJIRIj5xICJEeOZEQIj1yIiFEeuREQoj0yImEEOmREwkh0iMnGmW2HagF29/9+eeFxQf/8d93T7z3M9LMBL+auWtVLv3tvq9iia+WHvocVkcmE9hyFxIn3l9rmVV2zdz9r9n6Xms2qPX+wr1d7gR2/HZd3QsL91DspT+uYHv1xgMWEyOGnGiUGT9WH9LvfnzPthz5L/3PCsZ5rWEowDvR828+Sv9QrW/NQbClTfgcn2iVZgItB3ZmJeGPTBz8w0rQeFBAjCRyohEnGNWxEzHfO5HfbsuNyX+09Lt/ufe7ubV5kHcNpjGxwhYzLzogM9EU5jhWOK6FyREPgVrPv3UX7oPz5LnJiUYbOdGIw6cee/ahL8Ag6ESWb/MgegENC3thN1aMXuBzrLolSN2/3lrLgevZXsx32tTC/CvYhUasHT2XjTZyIiFEeuREQoj0yImEEOmREwkh0iMnEkKkR04khEiPnEgIkR45kRAiPWmc6N848L9XV+5npeXH2uqtO2FY2nOrtvqvO6UOWqegj8VhfCwl75l3u41bj6RxInzVrPS6E4WlPbdXFLSO1emggt2HTZRPq6tZtRZGZqNJ40QPdblzxZFpQ1hZKqCf7oZhbI/ukVSnDt47cqKUiiPThrCyVEByou4kJyqX4si0IawsFZCcqDvJicqlODJtCCtLBSQn6k5yonIpjkwbwspSAcmJupOcqFyKI9OGsLJUQHKi7iQnKqqFT69UnngShDs6lzVy8NjM+j0brjgybQgrd6XiQfPReGyt02fOhVlO1xa/+Obb78PcgWjwTnTyrVPonFmjX/m4MX3g6LpuNvheV0RyoqLiRf1rfsnRy/1V53b2gzkkqtVl6wpIfN0YD76KL4BuFJRkzu7nprePT1j546+d9OW7VhyZNoSVOxe/aXX5NtM+PnR25ts3ZRBsqLDAzolndz+311rwCcQ8y2O1dWyHtfl1HmoWGLwG70TQ1rHxqRcO8SsjzSAzDlnDiZBmuCzOm0pldyIM7BhesEC0Ehsz3FoC24ON653lY8Pv8lWwtX7gM7nFzXxq32Eca/bCxSy/89tenFjvHSiOTBvCyl0piFLgpLbXCvgEBAtGNE6fOW/OhZGW1SNc9ybGHGHBXiuA4POjNTJIJXEihpFd1yaDFls4USN0db/24d08KrsTNVXTS8XMwIn8R5vdcMvEpcvzvjq3bZyICUwi2Jrd1rD9+z+u+2LdKY5MG8LKnYtna7diS9tHC5TlZPnUplqtT6MQXj56YJYUzEPpRIwSR6CfZCH9USPyA1YSJ4L5+hthEFs4ET0Ihm57N5vkRE3U6lLhMcHutPQgZvJpwrq+34V5MtM+n8Osnli+zd87UNKK8Z42e2EOk6Os8ajCLe/2VrILxZFpQ1i5K+FbH3/19azxFfh4mzV+3UCmPYthLNlepC0mSNNxglBkjZgjjUjCqRE6HI4xZ4HBK4kTmRgc3P8QMYst59eIDDsPJ93r66WXnGhNvOXydhruGyHFkWlDWFkqoLRONLySE62pfl/Npyr+eWH0FEemDWFlJzwcBYQlyio5UXeSEz3SaHsQFUemDWFlpyBQwe/QZVa/nKhpV5zadyjMGhXJiZqoaScYDcWRaUNY2Qkh4s8QRE5k2lAn4s/SIyk5URO16AQv80dWn1n8tXqRsWrHbXoCRfTYinFk2hBWdio4J4JJ0bMsp/jPcI/9LtQ3334f/zhtv8j6VwFck7XR2ggnquRv6EnTsPgf/mNtxLOzvX7pl8ruRLYKDon2K+Ls1cPshfp76OOvrnVr5Ld6ExGscmSCg3b2g7l4/MSF+fI1awzgqV+vrV7DQa06ylgvrA/7oy8z3VRfLT0syPixWljZqVWUYrEkv/Xf/3Gd79oZsUrj/cDWsXEud+C7MxauuEUSbAQjiosA+HY/azgOi50+c44xQRkzIKtbrd7mhIJvJCmG15ZKZPmhrUDjJd3eSr6yFMWKTEngRHEwW7Gw+KCgE8Ur1LzYe5m2AhZ5Hzfa8eyFi9ZP8H35cs3LIpy5t5AIlw9s5u5AvRtT2Z2oU+ECXFv8Ymdj1W+2tgJ47ddur7wHTAN2gmDWwF0+J2sMG1zU/CjXfRkMOQwM7sry1tggjs5OwC7C6o9ajBRHphVXbzwIKzsF44Hry32OyecjaOjN8KOpFw7x29GJbIzZSwNuK/kI9IPQEr5lfmUfLq7q9lXqKwYiH8HJoAoszBYredlRuDiAKyofq47mRLD7gk6Eb8RvF59nICtg508zzRrOS/u2cDXtirbsCwnEjTdOFrPbQ9PyXUtOVFS4aTP66BO8upbPC2zriaz345pxuVClsdAe1zLoB5l7amAtv4TPZgfcxk6Un0m9TSuTtX1mjCPThrByQ/yC9jXx1Vo9NWSNUzrYWOZrT2eVfEIUOJGvZZlcaG5740QQ0u1ulmoVcSBcOLgJom0VeSmzPJ52nn7S5E+p4HNlR05UK/x0ZjS907SKD9Psq5bPFuyK4LvHa6/NWXznREnrabgf47Fgat/aJJ0rSxu1u5GcaKDipCDI9D1goxVHpg1h5YZ8n0MXRKfc6K+w0e33URvhRKZ4WtdGTVvgMuumavUjQ0HFE6uOJCcql+LItCGs3BCeBHm/hbHaNE2i+uVEDGxMWG5UJCcql+LItCGsLBVQv5yobJITlUtxZNoQVpYKSE7UneRE5VIcmTaElTvXtcUvwqyGCj5r+Jcy8Y+1fGPYkey1Wrb+9Jqej72gDPLbaNM60eyF+osF+zj1QpfLtf2vhMEb4V4kJyqX4si0IazcuSr5Qq2DR1+2QY7Bb6+Bmbl1bIet6PFLeyqNP7jDMtsbS6iQRiZ/+D9wdOb4a6+zyu7G35ajUKBarf9xFd+g/ZEWNshz4PIIfvRvkVgXp4Sj2FewN+KtlMSJcKoWVa42sN/vKvliKH4XBrOSv4CjiTAOfI9Gi/ExtG/KYkyj2G63rqLHV2amsjjR3fvhNy+n4si0Iazcudj1uaqAXfb0mfNmPRwSWeO1C/KRcy3/M0x+PUvWGDz2dsZGyIHGHwzJ1q9dsHFie60KtTVfDsrG+ScN/dBlwlwMBewrPHa9chInMtnJUwvr/+Sxn2AyMgysfyXH+Jt4gbbmC6+YY21axPqisjhRf6/3kKrTix3W71x0H9yl7eUx+645EZ+P2N0xNq4tPhoGs/lqSRs8lXzllKWZ8E7kC3AZl/1ho6xxJv45a3u+aL5aXQ6ciPd8bL0T2bLGzelEOycmQZYH1ttNlofCpjN2Y5jad9jHzZzILzHhd+cum4RmeXzY4PFXH63M6l2dds7eSeNEZHmlvNxZCaPxWMLOsrlVH1Gt/+3VwJTEifqlPv7u06nK5USiI8LOIhXQUDtRQsmJREvCziIVkJyoO8mJREvCziIVkJyoO8mJREvCziIVkJyoO8mJREvCziIVkJyoO8mJREvCziIVkJyoO8mJREs0SLpQpyPqzoqCnN2qhWEZAHKiYQLjShTnx65GFGrFTZWKLha79Y6cSAiRHjmRECI9ciIhRHrkREKI9MiJhBDpkRMJIdIjJxJCpEdOJIRIj5xoRKg88WSQ8CzdXOYuJK5c/Rzps7NzcTEy/8lncWZ7fGtW/eldz8YlW7HtqQlgH1985fW4jOeZyb1xphhe5EQjgnci8KcP6/9b94k3TtmuL298hwS2AB+5i4MfOVeuXkcCW5QxK/HWYGm2BkfbM33Y9qIKWLpZ5SF8FWYyh1VgW/uPzAQtY4tidDS08MzktO2q1U1tkgmeds19X1ThEe18cCZbxnYwLYYFOdGQ8cvf/BPE+YETMeGdiInAiawAEmZASAS+A/YfeRn2QTtjGeZbFebETrQl/8v81hosBsA+LNM7EcvU6lOeuhPFE7fYiSzfjov5lHc6MRTIiYYJ2lBTM6IBYUDSC/jR8q2MOREmNVvGxs2Jfv/OuVpuB0iYp3CKxLooCXfwTrRn+pBNPWInQoIW48/EtuY7PBMW9gXYiDmRnQkOyvmRWRIq8jTMiezriCFCTjQ0nPr4Ngzo/MKdU3+pJ+ICATbUhdj8yImGBj8VQmL7saW4jBBDipxoaAjmQUWmRUIMC3KioUFOJEYYOdHQwKez4+/9BJgICvBH3LOzc2dnLzLn7XfO1xo/GNneL29851+cBW/B+LsvM69cvY7y3LKu1arkCwWsJGsxhx/3TB/mr+OWuXSzaulKvrJp21MTPEPs8q/J7MTsnO33aTGqyImGifbvzmr1F9j1/5KYOXyjhKFuOZX8NRbH/J7pQ8yEI8AImIZxoAWmbV0iXIALI2ENZmqV/H08CxjI8bXsJV1QrLb+PVoAT2b/kRm+erODainjaCMnGhFaORFdg+trvBP5FTfeEfzbcZ9DI2BJe5fvJzKNVYtr0zFzoqawuh3CuxUPh9PbMjZekxOVBjnR6OAflOIcpPm4xEmHnwf5Rpg/ny+Y9gkr79ukWbRppw0o4KtwkTfhScKMbI2SPS3G7YjRQE4khEiPnEgIkR45kRAiPXIiIUR65ERCiPTIiYQQ6ZETCSHSIycSQqRHTiSESI+cSAiRHjmRECI9ciIhRHrkREKI9MiJhBDpkRMJIdIjJxJCpEdOJIRIj5xICJEeOZEQIj1yIiFEeupOlEmSJCXV7dtyIkmSUgtO9P88MtFLALUT6gAAAABJRU5ErkJggg==>