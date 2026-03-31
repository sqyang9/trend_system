# Exposure Engine 阶段总结

## 1. 阶段结论

`compression_breakout -> exhaustion / compound repair` 这条修复线已经正式收口，应冻结为 `promising-but-not-promotable archive`。最终最佳 compound repair 候选 `Core+CompoundRepair[close30_gate_to_base]` 相对 `Core+BinaryAddOn` 仍然只有 `dMaxDD -0.50pp`，没有跨过 promotion bar，虽然它的增益来自真实的 strong selection 改善，而不是简单去风险。

Exposure Engine 的 E1 结果显示，当前最优常数 AddOn 基线是 `Core+ConstAddOn[1.00x]`。它相对 `Core+BinaryAddOn` 不只是收益更高，而且回撤形态也更好：`TotalReturn 1330.99% vs 965.43%`，`MaxDD -63.70% vs -72.63%`，`Calmar 0.837 vs 0.637`，`Ulcer 30.33 vs 35.38`。这说明原先的 Binary AddOn 暴露水平是明显偏低，而不是“差一点点”。

Exposure Engine 的 E2 进一步确认：没有任何最小动态 schedule 真正打赢 `Core+ConstAddOn[1.00x]`。最优动态候选 `Core+DynamicExposure[trend_90dma_2state]` 仍然相对 `Const1x` 落后 `dReturn -90.06pp`、`dMaxDD -1.07pp`、`dCalmar -0.038`，驱动也主要是 exposure suppression，而不是更高效的 allocation。因此当前阶段的最终判断应是：`1.00x constant sleeve` 就是这条单 AddOn 架构下的有效前沿，`E3` 不应打开。

## 2. 这阶段真正学到了什么

这轮研究最重要的收获，不是“某个过滤器有没有点用”，而是把层级关系理顺了：

- 修复线有方向性价值，但不足以成为主前沿。`sq25_base_all` 和 `close30_gate_to_base` 都能继续改善 strong selection，但改善幅度已进入边际区，而且始终无法补平最后的 drawdown gap。
- 真正的组合前沿来自更高常数暴露，而不是更精细的低暴露修补。从 `0.50x`、`0.75x` 到 `1.00x`，组合层面的 `TotalReturn / MaxDD / Calmar / Ulcer` 持续改善，说明当前系统里 AddOn 不是“该少上”，而是“原先明显没上够”。
- 慢变量动态调度暂时没有 edge。你测试的 `drawdown-state`、`90DMA` 趋势背景、`90D AddOn` 质量这几类两态/三态调度，都没能超越 `1.00x constant`，说明在当前这条单 sleeve 架构下，轻量 timing 并没有带来更优的资本分配。
