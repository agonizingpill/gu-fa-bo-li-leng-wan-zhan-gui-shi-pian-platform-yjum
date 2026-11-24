        import {workspace} from '../workspace.js';
        import {el} from '../dom.js';

        const page = {
  "title": "弯模量程与校验",
  "module": "弯模与行程",
  "caption": "弯模与行程",
  "detail": "试制师须先校验标尺和有效行程，再登记试片或申请机位。介于量程外的曲线由系统拦截。",
  "path": "/jigs",
  "columns": [
    {
      "name": "code",
      "label": "编号"
    },
    {
      "name": "spread",
      "label": "台面跨度 mm"
    },
    {
      "name": "max_throw",
      "label": "最大行程 mm"
    },
    {
      "name": "calibrated",
      "label": "量具在校"
    }
  ],
  "layout": "flip",
  "view": "stack",
  "actions": [
    {
      "name": "calibrate",
      "label": "记入弯模量具检定",
      "path": "/jigs/calibrate",
      "fields": [
        {
          "name": "jig",
          "label": "弯模编号",
          "kind": "text",
          "initial": "CL-08"
        },
        {
          "name": "max_throw",
          "label": "实测行程 mm",
          "kind": "float",
          "initial": 25
        }
      ],
      "help": "校验最大行程。量程超过台面跨度三分之一时需拆检。",
      "roles": [
        "reviewer"
      ],
      "success": "已写入"
    }
  ]
};

        export const {title} = page;
        export const key = "jigs";
        export async function render(root, role) {
          await workspace(root, role, page);

        }
