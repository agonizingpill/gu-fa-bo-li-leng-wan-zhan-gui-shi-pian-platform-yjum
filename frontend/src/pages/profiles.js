        import {workspace} from '../workspace.js';

        const page = {
  "title": "温度 × 片厚 · 拟合曲线",
  "module": "预测曲线签注",
  "caption": "预测曲线签注",
  "detail": "按完整母板分组划分训练与留验，避免同块母板跨两侧造成虚低 MAE。可按拟合编号查询当时每块母板的去向或排除原因。",
  "path": "/profiles",
  "columns": [
    { "name": "code", "label": "编号" },
    { "name": "coupon", "label": "基准试片" },
    { "name": "prediction", "label": "拟合弯度 mm" },
    { "name": "mae", "label": "留出 MAE mm" },
    { "name": "plate_summary", "label": "母板分组" },
    { "name": "curve_summary", "label": "改善说明" },
    { "name": "token", "label": "拟合编号" }
  ],
  "layout": "split",
  "view": "grid",
  "actions": [
    {
      "name": "fit_curve",
      "label": "计算试片拟合曲线",
      "path": "/profiles/fit-curve",
      "fields": [
        { "name": "coupon", "label": "验证试片", "kind": "text", "initial": "GP-NEW" },
        { "name": "penalty", "label": "Lasso 正则强度", "kind": "float", "initial": 0.035 }
      ],
      "help": "拟合保温温度、片厚、目标弯度之间的二次交互；同一母板只会出现在训练或留验一侧。",
      "roles": ["operator", "reviewer"],
      "success": "已写入"
    },
    {
      "name": "plate_report_token",
      "label": "按拟合编号查母板去向",
      "path": "/profiles/plate-report",
      "report": true,
      "fields": [
        { "name": "token", "label": "拟合编号", "kind": "token", "initial": "" }
      ],
      "help": "读取该任务排队当时固化的母板分组，包括缺号隔离和异侧合并排除原因。",
      "roles": ["operator", "reviewer", "viewer"],
      "success": "查询完成"
    },
    {
      "name": "plate_report_profile",
      "label": "按曲线版本查母板去向",
      "path": "/profiles/plate-report",
      "report": true,
      "fields": [
        { "name": "code", "label": "曲线版本", "kind": "text", "initial": "PRO-24" }
      ],
      "help": "签注后的曲线 JSON 保存了当时的母板分组快照。",
      "roles": ["operator", "reviewer", "viewer"],
      "success": "查询完成"
    },
    {
      "name": "sign_profile",
      "label": "签注拟合曲线",
      "path": "/profiles/sign-profile",
      "fields": [
        { "name": "code", "label": "曲线版本", "kind": "text", "initial": "PRO-24" },
        { "name": "token", "label": "计算编号", "kind": "token", "initial": "" }
      ],
      "help": "核对留出误差和母板去向后签注曲线。一个计算编号只允许签注一次。",
      "roles": ["reviewer"],
      "success": "已写入"
    }
  ]
};

        export const {title} = page;
        export const key = "profiles";
        export async function render(root, role) {
          await workspace(root, role, page);
        }
