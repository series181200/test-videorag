import fs from "node:fs/promises";
import { FileBlob, SpreadsheetFile } from "@oai/artifact-tool";

const source = "D:/file/file/华科/作业/软件质量测试/test-videorag/outputs/vimo_test_documents_20260915/附录1：Vimo Desktop软件需求清单.xlsx";
const renderPath = "D:/file/file/华科/作业/软件质量测试/test-videorag/.artifact_work/requirements_tested_chain_final.png";
const lastRow = 19;

const workbook = await SpreadsheetFile.importXlsx(await FileBlob.load(source));
const sheets = await workbook.inspect({ kind: "sheet", include: "id,name" });
process.stdout.write(`SHEETS\n${sheets.ndjson}\n`);

const check = await workbook.inspect({
  kind: "table",
  range: `软件需求清单!A1:D${lastRow}`,
  include: "values,formulas",
  tableMaxRows: lastRow,
  tableMaxCols: 4,
  maxChars: 28000,
});
process.stdout.write(`TABLE\n${check.ndjson}\n`);

const errors = await workbook.inspect({
  kind: "match",
  searchTerm: "#REF!|#DIV/0!|#VALUE!|#NAME\\?|#N/A|#NUM!|#NULL!|#SPILL!|#CALC!",
  options: { useRegex: true, maxResults: 100 },
  summary: "final formula error scan",
});
process.stdout.write(`ERRORS\n${errors.ndjson}\n`);

const preview = await workbook.render({
  sheetName: "软件需求清单",
  range: `A1:D${lastRow}`,
  scale: 1.15,
  format: "png",
});
await fs.writeFile(renderPath, new Uint8Array(await preview.arrayBuffer()));
process.stdout.write(`RENDER ${renderPath}\n`);
