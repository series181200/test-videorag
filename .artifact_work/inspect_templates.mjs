import fs from "node:fs/promises";
import { FileBlob, SpreadsheetFile } from "@oai/artifact-tool";

const source = "D:/file/file/华科/作业/软件质量测试/第一阶段/实践作业-文档模板2025/实践作业-文档模板2025/附录1：软件需求清单模板.xlsx";
const outDir = "D:/file/file/华科/作业/软件质量测试/test-videorag/.artifact_work/xlsx_source_render";

const workbook = await SpreadsheetFile.importXlsx(await FileBlob.load(source));
const sheets = await workbook.inspect({ kind: "sheet", include: "id,name" });
process.stdout.write(`SHEETS\n${sheets.ndjson}\n`);
const names = [];
for (const line of sheets.ndjson.split(/\r?\n/)) {
  try {
    const item = JSON.parse(line);
    if (item.name) names.push(item.name);
  } catch {}
}
await fs.mkdir(outDir, { recursive: true });
for (const name of names) {
  const table = await workbook.inspect({
    kind: "table",
    range: `${name}!A1:Z100`,
    include: "values,formulas",
    tableMaxRows: 100,
    tableMaxCols: 26,
    maxChars: 30000,
  });
  process.stdout.write(`\nTABLE ${name}\n${table.ndjson}\n`);
  const style = await workbook.inspect({
    kind: "computedStyle",
    sheetId: name,
    range: "A1:Z30",
    maxChars: 8000,
  });
  process.stdout.write(`\nSTYLE ${name}\n${style.ndjson}\n`);
  const preview = await workbook.render({ sheetName: name, autoCrop: "all", scale: 1.5, format: "png" });
  await fs.writeFile(
    `${outDir}/${name.replace(/[\\/:*?\"<>|]/g, "_")}.png`,
    new Uint8Array(await preview.arrayBuffer()),
  );
}
