# 第三方组件与数据说明

## Apache ECharts

`frontend/assets/echarts.min.js` 从原项目原样保留，含 Apache 许可头。按内嵌的 ECharts 5.4.3 版本信息补充同标签上游 LICENSE 和 NOTICE。文件亦包含底层渲染组件 zrender 5.4.4 的版本信息。

- [许可证](third_party/echarts/LICENSE)
- [版权声明](third_party/echarts/NOTICE)
- 上游来源：`https://github.com/apache/echarts/tree/5.4.3`

此许可针对第三方组件，不替代原创代码许可证决定。

## 评分规则表

`national_fitness_standard.json` 标注《国家学生体质健康标准（2014年修订）》，沿用原数据。本轮未核实最初采集来源、版本覆盖及逐项准确性，不能宣称全面符合最新标准；正式发布前应补充可核对的来源与复核记录。

## Python 依赖

`backend/requirements.txt` 保留原版本约束。依赖由用户安装，不附带环境或二进制副本；各依赖许可由上游规定。
