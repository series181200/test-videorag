import fs from "node:fs/promises";
import { FileBlob, SpreadsheetFile } from "@oai/artifact-tool";

const source = "D:/file/file/华科/作业/软件质量测试/第一阶段/实践作业-文档模板2025/实践作业-文档模板2025/附录1：软件需求清单模板.xlsx";
const outputDir = "D:/file/file/华科/作业/软件质量测试/test-videorag/outputs/vimo_test_documents_20260915";
const outputPath = `${outputDir}/附录1：Vimo Desktop软件需求清单.xlsx`;
const previewPath = "D:/file/file/华科/作业/软件质量测试/test-videorag/.artifact_work/requirements_tested_chain_preview.png";

// 仅保留当前自动化测试实际覆盖的核心业务链路。
const rows = [
  ["启动与配置", "首次启动初始化", "系统应在未配置时显示初始化界面，保存存储目录和模型服务配置后进入主界面。", "Renderer"],
  ["启动与配置", "后端服务连接", "系统应启动本地 Python 服务并执行健康检查，向页面返回可用或失败状态。", "Renderer → Communication → API"],
  ["启动与配置", "ImageBind 状态", "系统应检查、加载并返回 ImageBind 状态；模型不可用时应阻止后续视频分析。", "Communication → API"],

  ["视频导入", "视频文件选择", "用户应能选择一个或多个视频，系统应返回正确的文件名、完整路径、大小和选择顺序。", "Renderer → Communication"],
  ["视频导入", "路径与重复处理", "系统应正确处理 Windows 路径、中文目录和多点文件名，并避免同一路径的视频被重复加入。", "Renderer → Communication"],
  ["视频导入", "上传参数传递", "系统应将会话标识、视频路径列表和存储目录转换为 Python API 所需参数并提交。", "Renderer → Communication → API"],

  ["视频分析与索引", "异步索引任务", "后端收到有效上传请求后应启动独立索引任务，并按会话隔离任务与数据。", "API"],
  ["视频分析与索引", "视频分段与文本生成", "算法应对视频进行分段，提取音频转写和片段描述，为知识索引提供文本。", "API → Algorithm"],
  ["视频分析与索引", "Token 分块", "算法应按照 Token 上限和重叠规则生成有序文本块，边界输入不得产生无效空块。", "Algorithm"],
  ["视频分析与索引", "多模态索引", "算法应使用 ImageBind 生成片段特征，并建立实体、关系和向量等检索数据。", "Algorithm"],
  ["视频分析与索引", "索引数据持久化", "算法处理结果应写入会话工作目录，重新加载后仍能用于查询。", "Algorithm"],
  ["视频分析与索引", "分析状态反馈", "索引过程中应持续保存处理状态和已完成视频，前端轮询后显示处理中、完成或失败。", "API → Communication → Renderer"],

  ["视频检索与问答", "问题提交与校验", "用户提交非空问题后，系统应将问题发送到对应会话；无效输入不得启动查询任务。", "Renderer → Communication → API"],
  ["视频检索与问答", "检索与回答生成", "算法应检索相关文本和视频片段，并调用模型生成问题回答。", "API → Algorithm"],
  ["视频检索与问答", "回答状态与展示", "查询完成后，回答应沿 API 和 IPC 链路返回并显示在当前会话；失败时应显示错误。", "Algorithm → API → Communication → Renderer"],

  ["会话与资源管理", "会话持久化", "系统应保存和恢复会话标题、消息、视频与更新时间，并保持会话间数据隔离。", "Renderer → Communication"],
  ["会话与资源管理", "删除与终止", "删除会话时应移除本地数据，并终止该会话的索引、查询进程和轮询任务。", "Renderer → Communication → API"],
  ["异常与安全", "错误传播与资源释放", "任一层发生异常时应返回可序列化的错误并释放并发资源；IPC 应限制未授权通道，日志不得泄露 API Key。", "全链路"],
];

const workbook = await SpreadsheetFile.importXlsx(await FileBlob.load(source));
const sheet = workbook.worksheets.getItem("软件需求清单");
const lastRow = rows.length + 1;

sheet.getRange(`A2:D${lastRow}`).values = rows;
const full = sheet.getRange(`A1:D${lastRow}`);
full.format.font = { name: "宋体", size: 10 };
full.format.wrapText = true;
full.format.verticalAlignment = "top";
full.format.borders = { preset: "all", style: "thin", color: "#D9E2F3" };

const header = sheet.getRange("A1:D1");
header.format.font = { name: "宋体", size: 11, bold: true, color: "#FFFFFF" };
header.format.fill = "#1F4E78";
header.format.horizontalAlignment = "center";
header.format.verticalAlignment = "center";
header.format.rowHeight = 26;

sheet.getRange(`A2:D${lastRow}`).format.horizontalAlignment = "left";
sheet.getRange("A:A").format.columnWidth = 20;
sheet.getRange("B:B").format.columnWidth = 28;
sheet.getRange("C:C").format.columnWidth = 72;
sheet.getRange("D:D").format.columnWidth = 34;
sheet.getRange(`A2:D${lastRow}`).format.autofitRows();
sheet.freezePanes.freezeRows(1);

await fs.mkdir(outputDir, { recursive: true });
const preview = await workbook.render({
  sheetName: "软件需求清单",
  range: `A1:D${lastRow}`,
  scale: 1.25,
  format: "png",
});
await fs.writeFile(previewPath, new Uint8Array(await preview.arrayBuffer()));

const output = await SpreadsheetFile.exportXlsx(workbook);
await output.save(outputPath);
process.stdout.write(`OUTPUT ${outputPath}\nPREVIEW ${previewPath}\nROWS ${rows.length}\nLAST_ROW ${lastRow}\n`);
