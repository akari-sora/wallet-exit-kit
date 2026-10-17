# 07 常用常數

所有值都是公開標準（由函式／事件簽章算 keccak256 得到）。使用前可自行重算驗證。

## 公開合約（多數 EVM 鏈同一地址；每條鏈先用 eth_getCode 確認有部署）

| 名稱 | 地址 |
|---|---|
| Multicall3 | `0xcA11bde05977b3631167028862bE2a173976CA11` |
| Uniswap Permit2 | `0x000000000022D473030F116dDEE9F6B43aC78BA3` |

其他協議的地址一律從官方文件取得，並在鏈上核對；不要從本檔以外的記憶或搜尋摘要抄。`exitkit rpc` 的 `multicall_read` 會先確認 Multicall3 有部署，沒部署＝每一項都是未知。

## Event topic0

| 事件 | topic0 |
|---|---|
| `Transfer(address,address,uint256)`（ERC-20／721 共用） | `0xddf252ad1be2c89b69c2b068fc378daa952ba7f163c4a11628f55a4df523b3ef` |
| `Approval(address,address,uint256)`（ERC-20／721 共用） | `0x8c5be1e5ebec7d5bd14f71427d1e84f3dd0314c0f7b2291e5b200ac8c7c3b925` |
| `ApprovalForAll(address,address,bool)` | `0x17307eab39ab6107e8899845ad3d59bd9653f200f220920489ca2b5937696c31` |
| `TransferSingle(address,address,address,uint256,uint256)` | `0xc3d58168c5ae7397731d063d5bbf3d657854427343f4c083240f7aacaa2d0f62` |
| `TransferBatch(address,address,address,uint256[],uint256[])` | `0x4a39dc06d4c0dbc64b70af90fd698a233a518aa5d07e595d983b8c0526c8f7fb` |
| Permit2 `Approval(address,address,address,uint160,uint48)` | `0xda9fa7c1b00402c17d0161b249b1ab8bbec047c5a52207b9c112deffd817036b` |
| Permit2 `Permit(address,address,address,uint160,uint48,uint48)` | `0xc6a377bfc4eb120024a8ac08eef205be16b817020812c73223e81d1bdb9708ec` |
| Permit2 `Lockdown(address,address,address)` | `0x89b1add15eff56b3dfe299ad94e01f2b52fbcb80ae1a3baea6ae8c04cb2b98a4` |
| `BorrowAllowanceDelegated(address,address,address,uint256)`（Aave 系信用委託） | `0xda919360433220e13b51e8c211e490d148e61a3bd53de8c097194e458b97f3e1` |
| ERC-4626 `Deposit(address,address,uint256,uint256)` | `0xdcbc1c05240f31ff3ad067ef1ee35ce4997762752e3a095284754544f4c709d7` |
| ERC-4626 `Withdraw(address,address,address,uint256,uint256)` | `0xfbde797d201c681b91056529119e0b02407c7bb96a4a2c75c01fc9667232c8db` |
| Safe `ExecutionSuccess(bytes32,uint256)` | `0x442e715f626346e8c54381002da614f62bee8d27386535b2521ec8540898556e` |
| `Upgraded(address)`（EIP-1967） | `0xbc7cd75a20ee27fd9adebab32041f755214dbc6bffa90cc0225b39da2e5c2d3b` |
| `AdminChanged(address,address)`（EIP-1967） | `0x7e644d79422f17c01e4894b5f4f588d331ebfa28653d42ae832dc59e38c9798f` |

## Function selector

| 函式 | selector |
|---|---|
| `balanceOf(address)` | `0x70a08231` |
| `allowance(address,address)` | `0xdd62ed3e` |
| `approve(address,uint256)` | `0x095ea7b3` |
| `transfer(address,uint256)` | `0xa9059cbb` |
| `transferFrom(address,address,uint256)` | `0x23b872dd` |
| `decimals()`／`symbol()`／`name()` | `0x313ce567`／`0x95d89b41`／`0x06fdde03` |
| `isApprovedForAll(address,address)` | `0xe985e9c5` |
| `setApprovalForAll(address,bool)` | `0xa22cb465` |
| Permit2 `allowance(address,address,address)` | `0x927da105` |
| Permit2 `approve(address,address,uint160,uint48)` | `0x87517c45` |
| Permit2 `lockdown((address,address)[])` | `0xcc53287f` |
| Permit2 `transferFrom(address,address,uint160,address)` | `0x36c78516` |
| Permit2 `invalidateNonces(address,address,uint48)` | `0x65d9723c` |
| Permit2 `invalidateUnorderedNonces(uint256,uint256)` | `0x3ff9dcb1` |
| EIP-2612 `permit(...)` | `0xd505accf` |
| `DOMAIN_SEPARATOR()`／`nonces(address)` | `0x3644e515`／`0x7ecebe00` |
| Multicall3 `aggregate3((address,bool,bytes)[])` | `0x82ad56cb` |
| Multicall3 `getEthBalance(address)` | `0x4d2301cc` |
| ERC-4626 `asset()`／`convertToAssets(uint256)`／`maxRedeem(address)`／`previewRedeem(uint256)` | `0x38d52e0f`／`0x07a2d13a`／`0xd905777e`／`0x4cdad506` |
| Aave 系 `approveDelegation(address,uint256)`／`borrowAllowance(address,address)` | `0xc04a8a10`／`0x6bd76d24` |
| Aave 系 Pool `getUserAccountData(address)`／`getReserveData(address)`／`getConfiguration(address)` | `0xbf92857c`／`0x35ea6a75`／`0xc44b11f7` |
| Safe `getOwners()`／`getThreshold()`／`nonce()` | `0xa0e67e2b`／`0xe75235b8`／`0xaffed0e0` |

## Storage slot

| 用途 | slot |
|---|---|
| EIP-1967 implementation | `0x360894a13ba1a3210667c828492db98dca3e2076cc3735a920a3ca505d382bbc` |
| EIP-1967 admin | `0xb53127684a568b3173ae13b9f8a6016e243e63b6e8ee1178d6a717850b5d6103` |
| EIP-1967 beacon | `0xa3f0ad74e5423aebfd80d3ef4346578335a9a72aeaee59ff6cb3582b35133d50` |

## Aave V3 系 reserve configuration 位元（`getConfiguration(asset)` 回傳的 uint256）

| 位元 | 意義 |
|---|---|
| 56 | active |
| 57 | frozen |
| 58 | borrowing enabled |
| 60 | paused |

fork 版本可能改過，以該協議原始碼為準並用模擬確認。

## 特殊值
- 無上限授權常見值：`2^256-1`（ERC-20）、`2^160-1`（Permit2 amount）。部分 token 對無上限不扣額度。
- EIP-7702 委託帳戶的 code：`0xef0100` ＋ 20 bytes 委託目標（共 23 bytes）。
- eth_simulateV1 `traceTransfers` 的原生幣假事件發出者：`0xEeeeeEeeeEeEeeEeEeEeeEEEeeeeEeeeeeeeEEeE`。
