<!--
  PlannerView 已废弃（W2 多页面系统重构）

  旧职责："选模板 → 逐日编排 → 保存" 三步向导，单页堆叠
  新方案：
    选模板：TemplatePickerSheet.vue（弹层）从 /plans 触发
    编排+保存：TripEditView (/trip/:id/edit) 复用 TripDayEditor 组件
    路由：/planner → /plans?new=1（见 router/index.js redirect）

  本文件保留为占位，防止任何旧 import 仍指向它。
  实际不会被任何路由引用到。
-->
<template><div /></template>
<script setup>
// noop
</script>
