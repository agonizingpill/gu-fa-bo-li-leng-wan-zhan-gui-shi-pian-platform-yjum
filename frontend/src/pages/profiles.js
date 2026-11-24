        import {workspace} from '../workspace.js';
        import {el} from '../dom.js';

        const page = {
  "title": "温度 × 片厚 · 拟合曲线",
  "module": "预测曲线签注",
  "caption": "预测曲线签注",
  "detail": "将非线性交互与线性项同时纳入 Lasso，留下末段温区用于误差比较。",
  "path": "/profiles",
  "columns": [
    {
      "name": "code",
      "label": "编号"
    },
    {
      "name": "coupon",
      "label": "基准试片"
    },
    {
      "name": "prediction",
      "label": "拟合弯度 mm"
    },
    {
      "name": "mae",
      "label": "留出 MAE mm"
    },
    {
      "name": "curve",
      "label": "改善说明"
    },
    {
      "name": "token",
      "label": "拟合编号"
    }
  ],
  "layout": "split",
  "view": "grid",
  "actions": [
    {
      "name": "fit_curve",
      "label": "计算试片拟合曲线",
      "path": "/profiles/fit-curve",
      "fields": [
        {
          "name": "coupon",
          "label": "验证试片",
          "kind": "text",
          "initial": "GP-NEW"
        },
        {
          "name": "penalty",
          "label": "Lasso 正则强度",
          "kind": "float",
          "initial": 0.035
        }
      ],
      "help": "拟合保温温度、片厚、目标弯度之间的二次交互。",
      "roles": [
        "operator",
        "reviewer"
      ],
      "success": "已写入"
    },
    {
      "name": "sign_profile",
      "label": "签注拟合曲线",
      "path": "/profiles/sign-profile",
      "fields": [
        {
          "name": "code",
          "label": "曲线版本",
          "kind": "text",
          "initial": "PRO-24"
        },
        {
          "name": "token",
          "label": "计算编号",
          "kind": "token",
          "initial": ""
        }
      ],
      "help": "核对留出误差后签注曲线。一个计算编号只允许签注一次。",
      "roles": [
        "reviewer"
      ],
      "success": "已写入"
    }
  ]
};

        export const {title} = page;
        export const key = "profiles";
        export async function render(root, role) {
          await workspace(root, role, page);

        }
