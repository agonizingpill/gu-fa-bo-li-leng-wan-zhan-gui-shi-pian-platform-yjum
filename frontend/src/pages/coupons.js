        import {workspace} from '../workspace.js';

        const page = {
  "title": "冷却后的尺规测量",
  "module": "温区试片",
  "caption": "温区试片",
  "detail": "见证时登记母板号；同一块母板的新片沿用原有训练/留验分组。缺号旧片先隔离，复核员合并异侧母板号后整板退出拟合。",
  "path": "/coupons",
  "columns": [
    { "name": "code", "label": "试片编号" },
    { "name": "plate", "label": "母板号" },
    { "name": "jig", "label": "弯模" },
    { "name": "heat", "label": "保温温度 °C" },
    { "name": "thick", "label": "片厚 mm" },
    { "name": "target", "label": "目标弯度 mm" },
    { "name": "measured", "label": "冷却弯度 mm" },
    { "name": "locked", "label": "已确认" },
    { "name": "side_label", "label": "母板分组" },
    { "name": "detail", "label": "隔离/排除原因" }
  ],
  "layout": "stack",
  "view": "table",
  "actions": [
    {
      "name": "record_coupon",
      "label": "登记冷却试片",
      "path": "/coupons/record-coupon",
      "fields": [
        { "name": "code", "label": "试片编号", "kind": "text", "initial": "GP-NEW" },
        { "name": "jig", "label": "弯模编号", "kind": "text", "initial": "CL-44" },
        { "name": "heat", "label": "保温温度 °C", "kind": "float", "initial": 520 },
        { "name": "thick", "label": "片厚 mm", "kind": "float", "initial": 4 },
        { "name": "target", "label": "目标弯度 mm", "kind": "float", "initial": 10 },
        { "name": "measured", "label": "实测弯度 mm", "kind": "float", "initial": 8.4 }
      ],
      "help": "冷却后以同一尺规记录目标和实弯；母板号在复核员见证时登记。",
      "roles": ["operator", "reviewer"],
      "success": "已写入"
    },
    {
      "name": "witness",
      "label": "确认尺规测量并登记母板",
      "path": "/coupons/witness",
      "fields": [
        { "name": "coupon", "label": "试片编号", "kind": "text", "initial": "GP-NEW" },
        { "name": "plate", "label": "母板号", "kind": "text", "initial": "MB-NEW" }
      ],
      "help": "同一母板号的新试片自动沿用首次分组；不填母板号的旧试片将被隔离。",
      "roles": ["reviewer"],
      "success": "已见证"
    },
    {
      "name": "merge_plates",
      "label": "合并母板号",
      "path": "/coupons/merge-plate",
      "report": true,
      "fields": [
        { "name": "source", "label": "重复/待合并母板号", "kind": "text", "initial": "MB-OLD" },
        { "name": "target", "label": "保留母板号", "kind": "text", "initial": "MB-NEW" }
      ],
      "help": "两个号若原来分别去过训练和留验，合并后的整板试片都会退出后续拟合。",
      "roles": ["reviewer"],
      "success": "已合并"
    }
  ]
};

        export const {title} = page;
        export const key = "coupons";
        export async function render(root, role) {
          await workspace(root, role, page);
        }
