<script setup>
/**
 * 真实地图组件：Leaflet + 高德瓦片（无需 JS API Key）。
 * 接收带坐标的停留点列表，按天着色、编号、连线，自动缩放到覆盖范围。
 * 无坐标的点位自动忽略（不报错、不显示）。
 */
import { ref, onMounted, onBeforeUnmount, watch, nextTick } from 'vue'
import L from 'leaflet'
import 'leaflet/dist/leaflet.css'

const props = defineProps({
  spots: { type: Array, default: () => [] }, // [{ name, lat, lng, day, cat }]
  height: { type: String, default: '440px' },
})

const mapEl = ref(null)
let map = null
let markerGroup = null
let lineGroup = null

const DAY_COLORS = ['#4C7A5A', '#5C7A9D', '#B08968', '#8B7A9E', '#6B9A7E', '#C1857E', '#7B8DA0']
const dayColor = (day) => DAY_COLORS[(day - 1) % DAY_COLORS.length]

function buildMap() {
  if (map || !mapEl.value) return
  map = L.map(mapEl.value, { zoomControl: true, scrollWheelZoom: true })
  L.tileLayer('https://webrd0{s}.is.autonavi.com/appmaptile?lang=zh_cn&size=1&scale=1&style=8&x={x}&y={y}&z={z}', {
    subdomains: '1234',
    attribution: '© 高德地图',
    maxZoom: 18,
  }).addTo(map)
  markerGroup = L.layerGroup().addTo(map)
  lineGroup = L.layerGroup().addTo(map)
  render()
}

function render() {
  if (!map || !markerGroup) return
  markerGroup.clearLayers()
  lineGroup.clearLayers()
  const located = props.spots.filter(s => s.lat != null && s.lng != null &&
    !isNaN(parseFloat(s.lat)) && !isNaN(parseFloat(s.lng)))
  if (!located.length) {
    map.setView([39.9, 116.4], 10)
    return
  }
  // 按天分组连线
  const byDay = {}
  located.forEach(s => { (byDay[s.day] = byDay[s.day] || []).push(s) })
  for (const [day, stops] of Object.entries(byDay)) {
    const color = dayColor(Number(day))
    stops.forEach((s, i) => {
      L.marker([parseFloat(s.lat), parseFloat(s.lng)], {
        icon: L.divIcon({
          className: '',
          html: `<div style="width:26px;height:26px;border-radius:50%;background:${color};color:#fff;display:flex;align-items:center;justify-content:center;font-size:11px;font-weight:bold;border:2px solid #fff;box-shadow:0 1px 4px rgba(0,0,0,.3)">${i + 1}</div>`,
          iconSize: [26, 26], iconAnchor: [13, 13],
        }),
      }).addTo(markerGroup).bindPopup(`<b>${s.name}</b><br/>D${s.day} · 第 ${i + 1} 站`)
    })
    if (stops.length > 1) {
      L.polyline(stops.map(s => [parseFloat(s.lat), parseFloat(s.lng)]), {
        color, weight: 2.5, opacity: 0.7, dashArray: '6 6',
      }).addTo(lineGroup)
    }
  }
  // 自适应范围
  const bounds = L.latLngBounds(located.map(s => [parseFloat(s.lat), parseFloat(s.lng)]))
  map.fitBounds(bounds.pad(0.15))
}

onMounted(async () => { await nextTick(); buildMap() })
watch(() => props.spots, () => { if (map) render() }, { deep: true })
onBeforeUnmount(() => { if (map) { map.remove(); map = null } })
</script>

<template>
  <div ref="mapEl" :style="{ height, width: '100%', borderRadius: 'var(--r, 8px)', overflow: 'hidden' }"></div>
</template>
