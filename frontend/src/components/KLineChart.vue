<script setup lang="ts">
import { ref, onMounted, onUnmounted, watch, nextTick } from "vue";
import * as echarts from "echarts";
import type { ChartData } from "../types";

const props = defineProps<{
  data: ChartData | null;
}>();

const chartContainer = ref<HTMLElement | null>(null);
let chart: echarts.ECharts | null = null;

function dispose() {
  if (chart) {
    chart.dispose();
    chart = null;
  }
}

function buildOption(): echarts.EChartsOption | null {
  if (!props.data || !props.data.klines || props.data.klines.length === 0) {
    return null;
  }

  const {
    klines,
    ma5_series,
    ma10_series,
    ma20_series,
    ma60_series,
    macd_series,
    rsi_series,
    bollinger_series,
  } = props.data;
  const dates = klines.map((item) => item.date);
  const ohlc = klines.map((item) => [
    item.open,
    item.close,
    item.low,
    item.high,
  ]);
  const volumes = klines.map((item) => item.volume);

  // Colors for up/down candles
  const upColor = "#ef5350";
  const downColor = "#26a69a";

  function maColor(period: number): string {
    const colors: Record<number, string> = {
      5: "#fdd835",
      10: "#42a5f5",
      20: "#ab47bc",
      60: "#66bb6a",
    };
    return colors[period] || "#999";
  }

  return {
    animation: false,
    backgroundColor: "#1a1a2e",
    tooltip: {
      trigger: "axis",
      axisPointer: { type: "cross" },
    },
    axisPointer: {
      link: [{ xAxisIndex: "all" }],
      label: { backgroundColor: "#333" },
    },
    grid: [
      { left: "8%", right: "8%", top: "3%", height: "55%" },
      { left: "8%", right: "8%", top: "63%", height: "12%" },
      { left: "8%", right: "8%", top: "78%", height: "9%" },
      { left: "8%", right: "8%", top: "90%", height: "9%" },
    ],
    xAxis: [
      {
        type: "category",
        data: dates,
        gridIndex: 0,
        axisLine: { lineStyle: { color: "#555" } },
        axisLabel: {
          color: "#aaa",
          fontSize: 10,
          showMinLabel: true,
          showMaxLabel: true,
        },
        splitLine: { show: false },
      },
      {
        type: "category",
        data: dates,
        gridIndex: 1,
        axisLine: { lineStyle: { color: "#555" } },
        axisLabel: { show: false },
        splitLine: { show: false },
      },
      {
        type: "category",
        data: dates,
        gridIndex: 2,
        axisLine: { lineStyle: { color: "#555" } },
        axisLabel: { show: false },
        splitLine: { show: false },
      },
      {
        type: "category",
        data: dates,
        gridIndex: 3,
        axisLine: { lineStyle: { color: "#555" } },
        axisLabel: {
          color: "#aaa",
          fontSize: 10,
          showMinLabel: true,
          showMaxLabel: true,
        },
        splitLine: { show: false },
      },
    ],
    yAxis: [
      {
        scale: true,
        gridIndex: 0,
        splitLine: { lineStyle: { color: "#333" } },
        axisLabel: { color: "#aaa", fontSize: 10 },
      },
      {
        scale: true,
        gridIndex: 1,
        splitLine: { show: false },
        axisLabel: { show: false },
      },
      {
        scale: true,
        gridIndex: 2,
        splitLine: { lineStyle: { color: "#333" } },
        axisLabel: { color: "#aaa", fontSize: 10 },
      },
      {
        scale: true,
        gridIndex: 3,
        min: 0,
        max: 100,
        splitLine: { lineStyle: { color: "#333" } },
        axisLabel: { color: "#aaa", fontSize: 10 },
      },
    ],
    dataZoom: [
      {
        type: "inside",
        xAxisIndex: [0, 1, 2, 3],
        start: Math.max(0, 100 - 60),
        end: 100,
      },
    ],
    series: [
      // Grid 0: Candlestick
      {
        name: "K线",
        type: "candlestick",
        xAxisIndex: 0,
        yAxisIndex: 0,
        data: ohlc,
        itemStyle: {
          color: upColor,
          color0: downColor,
          borderColor: upColor,
          borderColor0: downColor,
        },
        markLine: {
          silent: true,
          symbol: "none",
          data: [
            ...(props.data?.support_levels || []).map((level) => ({
              yAxis: level,
              label: {
                formatter: `支撑 ${level}`,
                color: "#26a69a",
                fontSize: 10,
              },
              lineStyle: {
                color: "#26a69a",
                type: "dashed" as const,
                width: 1,
              },
            })),
            ...(props.data?.resistance_levels || []).map((level) => ({
              yAxis: level,
              label: {
                formatter: `阻力 ${level}`,
                color: "#ef5350",
                fontSize: 10,
              },
              lineStyle: {
                color: "#ef5350",
                type: "dashed" as const,
                width: 1,
              },
            })),
          ],
        },
      },
      // Grid 0: Bollinger Bands
      {
        name: "BOLL上轨",
        type: "line",
        xAxisIndex: 0,
        yAxisIndex: 0,
        data: bollinger_series.map((band) => band.upper),
        smooth: true,
        symbol: "none",
        lineStyle: { width: 1, color: "#78909c", type: "dashed" },
      },
      {
        name: "BOLL中轨",
        type: "line",
        xAxisIndex: 0,
        yAxisIndex: 0,
        data: bollinger_series.map((band) => band.middle),
        smooth: true,
        symbol: "none",
        lineStyle: { width: 1, color: "#78909c" },
      },
      {
        name: "BOLL下轨",
        type: "line",
        xAxisIndex: 0,
        yAxisIndex: 0,
        data: bollinger_series.map((band) => band.lower),
        smooth: true,
        symbol: "none",
        lineStyle: { width: 1, color: "#78909c", type: "dashed" },
      },
      // Grid 0: Moving Averages
      ...(
        ["ma5_series", "ma10_series", "ma20_series", "ma60_series"] as const
      ).map((key) => {
        const period = parseInt(key.replace("ma", "").replace("_series", ""));
        return {
          name: `MA${period}`,
          type: "line" as const,
          xAxisIndex: 0,
          yAxisIndex: 0,
          data: props.data![key] as number[],
          smooth: true,
          symbol: "none",
          lineStyle: { width: 1.5, color: maColor(period) },
        };
      }),
      // Grid 1: Volume
      {
        name: "成交量",
        type: "bar",
        xAxisIndex: 1,
        yAxisIndex: 1,
        data: klines.map((item, index) => ({
          value: item.volume,
          itemStyle: {
            color: item.close >= item.open ? upColor : downColor,
          },
        })),
      },
      // Grid 2: MACD
      {
        name: "MACD柱",
        type: "bar",
        xAxisIndex: 2,
        yAxisIndex: 2,
        data: macd_series.map((macdPoint) => ({
          value: macdPoint.histogram,
          itemStyle: {
            color: macdPoint.histogram >= 0 ? upColor : downColor,
          },
        })),
      },
      {
        name: "DIF",
        type: "line",
        xAxisIndex: 2,
        yAxisIndex: 2,
        data: macd_series.map((macdPoint) => macdPoint.dif),
        smooth: true,
        symbol: "none",
        lineStyle: { width: 1.5, color: "#42a5f5" },
      },
      {
        name: "DEA",
        type: "line",
        xAxisIndex: 2,
        yAxisIndex: 2,
        data: macd_series.map((macdPoint) => macdPoint.dea),
        smooth: true,
        symbol: "none",
        lineStyle: { width: 1.5, color: "#ffa726" },
      },
      // Grid 3: RSI
      {
        name: "RSI",
        type: "line",
        xAxisIndex: 3,
        yAxisIndex: 3,
        data: rsi_series,
        smooth: true,
        symbol: "none",
        lineStyle: { width: 1.5, color: "#ab47bc" },
        markLine: {
          silent: true,
          data: [
            {
              yAxis: 70,
              label: {
                show: true,
                formatter: "超买 70",
                color: "#ef5350",
                fontSize: 10,
              },
            },
            {
              yAxis: 30,
              label: {
                show: true,
                formatter: "超卖 30",
                color: "#26a69a",
                fontSize: 10,
              },
            },
          ],
          lineStyle: { color: "#555", type: "dashed" },
        },
      },
    ],
    legend: {
      data: [
        "K线",
        "MA5",
        "MA10",
        "MA20",
        "MA60",
        "BOLL上轨",
        "BOLL中轨",
        "BOLL下轨",
        "DIF",
        "DEA",
        "RSI",
      ],
      top: 0,
      left: "center",
      textStyle: { color: "#aaa", fontSize: 11 },
      selected: {
        BOLL上轨: false,
        BOLL中轨: false,
        BOLL下轨: false,
      },
    },
  };
}

function render() {
  if (!chartContainer.value) return;
  const option = buildOption();
  if (!option) return;

  if (!chart) {
    chart = echarts.init(chartContainer.value, undefined, {
      renderer: "canvas",
    });
  }
  chart.setOption(option, true);
  chart.resize();
}

watch(
  () => props.data,
  () => {
    nextTick(render);
  },
  { deep: false }
);

onMounted(() => {
  nextTick(render);
  window.addEventListener("resize", () => chart?.resize());
});

onUnmounted(dispose);
</script>

<template>
  <div class="kline-chart" ref="chartContainer" v-if="data"></div>
  <div v-else class="chart-empty">暂无图表数据</div>
</template>

<style scoped>
.kline-chart {
  width: 100%;
  height: 600px;
  background: #1a1a2e;
  border-radius: 8px;
}
.chart-empty {
  width: 100%;
  height: 300px;
  background: #1a1a2e;
  border-radius: 8px;
  display: flex;
  align-items: center;
  justify-content: center;
  color: #666;
  font-size: 14px;
}
</style>
