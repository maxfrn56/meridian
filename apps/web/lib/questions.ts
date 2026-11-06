export type ImportedQuestion = { prompt: string; tag: string };

const HEADER = /^(questions?|prompts?|requêtes?|requetes?)$/i;

/** Lit un CSV ou un texte : une question par ligne, étiquette éventuelle en deuxième colonne. */
export function parseQuestionFile(raw: string): ImportedQuestion[] {
  const seen = new Set<string>();
  const questions: ImportedQuestion[] = [];
  for (const line of raw.replace(/^\uFEFF/, "").split(/\r?\n/)) {
    if (!line.trim()) continue;
    const [promptCell = "", tagCell = ""] = splitCsvLine(line);
    const prompt = promptCell.replace(/\s+/g, " ").trim().slice(0, 400);
    const tag = tagCell.replace(/\s+/g, " ").trim().slice(0, 40);
    if (!prompt || HEADER.test(prompt) || prompt.length < 8 || seen.has(prompt)) continue;
    seen.add(prompt);
    questions.push({ prompt, tag });
  }
  return questions;
}

function splitCsvLine(line: string): string[] {
  const cells: string[] = [];
  let current = "";
  let quoted = false;
  for (let index = 0; index < line.length; index += 1) {
    const char = line[index];
    if (quoted) {
      if (char === '"' && line[index + 1] === '"') {
        current += '"';
        index += 1;
      } else if (char === '"') {
        quoted = false;
      } else {
        current += char;
      }
    } else if (char === '"') {
      quoted = true;
    } else if (char === "," || char === ";" || char === "\t") {
      cells.push(current.trim());
      current = "";
    } else {
      current += char;
    }
  }
  cells.push(current.trim());
  return cells;
}
