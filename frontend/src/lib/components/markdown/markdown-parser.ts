export function escapeHtml(text: string): string {
  return text.replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;");
}

function escapeHtmlAttribute(text: string): string {
  return escapeHtml(text).replace(/"/g, "&quot;").replace(/'/g, "&#39;");
}

const PRIVATE_DATA_BADGE = '<span class="private-data-badge">\u{1F6E1} $1</span>';

const PRIVATE_DATA_RE = /\{_\{(?:&quot;)?([^}"]+?)(?:&quot;)?\}_\}/g;
const PRIVATE_DATA_RAW_RE = /\{_\{"?([^}"]+?)"?\}_\}/;

/**
 * Replace {_{key}_} redaction placeholders with inline shield badges.
 * Works on plain text (no prior HTML escaping required).
 * Returns an HTML string safe for {@html ...}.
 */
export function highlightPrivateData(text: string): string {
  if (!text || !text.includes("{_{")) return escapeHtml(text);
  return escapeHtml(text).replace(PRIVATE_DATA_RE, PRIVATE_DATA_BADGE);
}

/**
 * Check whether text contains any {_{key}_} redaction placeholders.
 */
export function containsPrivateDataPlaceholders(text: string): boolean {
  return typeof text === "string" && PRIVATE_DATA_RAW_RE.test(text);
}

export function decodeHtml(text: string): string {
  return text
    .replace(/&quot;/g, '"')
    .replace(/&gt;/g, ">")
    .replace(/&lt;/g, "<")
    .replace(/&amp;/g, "&");
}

const SAFE_ABSOLUTE_LINK_PROTOCOLS = new Set(["http:", "https:", "mailto:", "tel:"]);
const MARKDOWN_LINK_BASE = "https://maivn.local";
const UNSAFE_MARKDOWN_HREF_CHARS = new Set(['"', "'", "`", "\\"]);

function hasUnsafeMarkdownHrefCharacter(value: string): boolean {
  for (const char of value) {
    const code = char.charCodeAt(0);
    if (code <= 31 || code === 127 || /\s/.test(char) || UNSAFE_MARKDOWN_HREF_CHARS.has(char)) {
      return true;
    }
  }
  return false;
}

function sanitizeMarkdownHref(rawHref: string): string | null {
  const decodedHref = decodeHtml(rawHref).trim();
  if (!decodedHref || hasUnsafeMarkdownHrefCharacter(decodedHref)) {
    return null;
  }

  try {
    const parsed = new URL(decodedHref, MARKDOWN_LINK_BASE);
    if (parsed.origin === MARKDOWN_LINK_BASE) {
      return escapeHtmlAttribute(decodedHref);
    }
    if (SAFE_ABSOLUTE_LINK_PROTOCOLS.has(parsed.protocol)) {
      return escapeHtmlAttribute(decodedHref);
    }
  } catch {
    return null;
  }

  return null;
}

function renderMarkdownLink(_match: string, label: string, rawHref: string): string {
  const href = sanitizeMarkdownHref(rawHref);
  if (href === null) {
    return label;
  }
  return `<a href="${href}" target="_blank" rel="noopener noreferrer">${label}</a>`;
}

function splitTableRow(line: string): string[] {
  const trimmed = line.trim().replace(/^\|/, "").replace(/\|$/, "");
  if (!trimmed) return [];
  return trimmed.split("|").map((cell) => cell.trim());
}

function isTableDivider(line: string): boolean {
  const trimmed = line.trim().replace(/^\|/, "").replace(/\|$/, "");
  if (!trimmed) return false;
  const cells = trimmed.split("|");
  if (cells.length < 2) return false;
  return cells.every((cell) => /^:?-{3,}:?$/.test(cell.trim()));
}

function parseAlignment(cell: string): "left" | "center" | "right" {
  const trimmed = cell.trim();
  const left = trimmed.startsWith(":");
  const right = trimmed.endsWith(":");
  if (left && right) return "center";
  if (right) return "right";
  return "left";
}

function renderTables(text: string): string {
  const lines = text.split("\n");
  const output: string[] = [];
  let i = 0;

  while (i < lines.length) {
    const line = lines[i];
    const next = lines[i + 1];
    const hasPipes = line?.includes("|");
    if (line && next && hasPipes) {
      const firstRowCells = splitTableRow(line);
      const firstRowColCount = firstRowCells.length;
      const nextHasPipes = next.includes("|");
      const dividerLine = nextHasPipes && isTableDivider(next);
      const isTable = firstRowColCount >= 2 && (dividerLine || nextHasPipes);

      if (isTable) {
        let alignments = dividerLine
          ? splitTableRow(next).map(parseAlignment)
          : Array(firstRowColCount).fill("left");

        const headerCells = dividerLine ? firstRowCells : null;
        const bodyRows: string[][] = dividerLine ? [] : [firstRowCells];

        i += dividerLine ? 2 : 1;

        while (i < lines.length && lines[i].includes("|")) {
          const rowCells = splitTableRow(lines[i]);
          if (rowCells.length === 0) break;
          bodyRows.push(rowCells);
          i += 1;
        }

        const columnCount = Math.max(
          headerCells?.length ?? 0,
          ...bodyRows.map((row) => row.length),
          0,
        );

        alignments = [...alignments];
        while (alignments.length < columnCount) {
          alignments.push("left");
        }

        const numericRegex = /^[\d$+-.%,]+[A-Za-z]*$/;
        const numericColumns = new Array(columnCount).fill(false).map((_, colIndex) => {
          let hasValue = false;
          for (const row of bodyRows) {
            const cell = row[colIndex] ?? "";
            const trimmed = cell.trim();
            if (!trimmed) continue;
            hasValue = true;
            if (!numericRegex.test(trimmed)) {
              return false;
            }
          }
          return hasValue;
        });

        const headerHtml = headerCells
          ? headerCells
              .map((cell, index) => {
                const baseAlign = alignments[index] ?? "left";
                const resolvedAlign =
                  baseAlign !== "left" ? baseAlign : numericColumns[index] ? "right" : "left";
                const style =
                  resolvedAlign && resolvedAlign !== "left"
                    ? ` style="text-align:${resolvedAlign}"`
                    : "";
                return `<th${style}>${cell}</th>`;
              })
              .join("")
          : "";

        const bodyHtml = bodyRows
          .map((row) => {
            const cells = row.map((cell, index) => {
              const baseAlign = alignments[index] ?? "left";
              const resolvedAlign =
                baseAlign !== "left" ? baseAlign : numericColumns[index] ? "right" : "left";
              const style =
                resolvedAlign && resolvedAlign !== "left"
                  ? ` style="text-align:${resolvedAlign}"`
                  : "";
              return `<td${style}>${cell}</td>`;
            });
            return `<tr>${cells.join("")}</tr>`;
          })
          .join("");

        const tableClass = headerCells
          ? "md-table md-table_has-header"
          : "md-table md-table_no-header";

        output.push(
          `<div class="md-table-wrap"><table class="${tableClass}">${headerHtml ? `<thead><tr>${headerHtml}</tr></thead>` : ""}${bodyHtml ? `<tbody>${bodyHtml}</tbody>` : ""}</table></div>`,
        );
        continue;
      }
    }

    output.push(line);
    i += 1;
  }

  return output.join("\n");
}

function createPlaceholder(html: string, placeholders: string[]): string {
  const index = placeholders.push(html) - 1;
  return `@@MDPLACEHOLDER${index}@@`;
}

function restorePlaceholders(text: string, placeholders: string[]): string {
  return text.replace(/@@MDPLACEHOLDER(\d+)@@/g, (_match, index: string) => {
    return placeholders[Number(index)] ?? "";
  });
}

function replaceUnderscoreDelimited(
  text: string,
  delimiter: "_" | "__",
  tagName: "em" | "strong",
): string {
  const pattern =
    delimiter === "__"
      ? /(^|[^\w])__(?!\s)([^\n]*?\S)__(?=[^\w]|$)/g
      : /(^|[^\w])_(?!\s)([^\n]*?\S)_(?=[^\w]|$)/g;

  return text.replace(pattern, (_match, prefix: string, inner: string) => {
    return `${prefix}<${tagName}>${inner}</${tagName}>`;
  });
}

function highlightCode(code: string, lang: string): string {
  const escaped = escapeHtml(code);
  const language = lang.toLowerCase();
  const pythonKeywords =
    /\b(def|class|if|elif|else|for|while|try|except|finally|with|as|import|from|return|yield|raise|pass|break|continue|and|or|not|in|is|None|True|False|lambda|async|await|global|nonlocal)\b/g;
  const jsKeywords =
    /\b(const|let|var|function|class|if|else|for|while|do|switch|case|break|continue|return|try|catch|finally|throw|new|delete|typeof|instanceof|in|of|async|await|import|export|default|from|extends|super|this|null|undefined|true|false|yield)\b/g;
  const sqlKeywords =
    /\b(SELECT|FROM|WHERE|JOIN|LEFT|RIGHT|INNER|OUTER|ON|AND|OR|NOT|IN|IS|NULL|AS|ORDER|BY|GROUP|HAVING|LIMIT|OFFSET|INSERT|INTO|VALUES|UPDATE|SET|DELETE|CREATE|TABLE|INDEX|DROP|ALTER|ADD|CONSTRAINT|PRIMARY|KEY|FOREIGN|REFERENCES|UNIQUE|DEFAULT|CASCADE|UNION|ALL|DISTINCT|COUNT|SUM|AVG|MIN|MAX|CASE|WHEN|THEN|ELSE|END)\b/gi;
  const bashKeywords =
    /\b(if|then|else|elif|fi|for|while|do|done|case|esac|function|return|exit|echo|cd|ls|rm|cp|mv|mkdir|chmod|chown|grep|sed|awk|cat|head|tail|sort|uniq|wc|find|xargs|export|source|alias)\b/g;
  const jsonKeywords = /\b(true|false|null)\b/g;

  let highlighted = escaped;

  if (["python", "py"].includes(language)) {
    highlighted = highlighted.replace(/^(\s*)(@\w+)/gm, '$1<span class="hl-decorator">$2</span>');
    highlighted = highlighted.replace(pythonKeywords, '<span class="hl-keyword">$1</span>');
    highlighted = highlighted.replace(
      /\b(print|len|range|str|int|float|list|dict|set|tuple|bool|type|isinstance|hasattr|getattr|setattr|open|input|format|sorted|reversed|enumerate|zip|map|filter|reduce|sum|min|max|abs|round|pow|divmod|hex|oct|bin|ord|chr)\b/g,
      '<span class="hl-builtin">$1</span>',
    );
  } else if (["javascript", "js", "typescript", "ts", "jsx", "tsx"].includes(language)) {
    highlighted = highlighted.replace(jsKeywords, '<span class="hl-keyword">$1</span>');
    highlighted = highlighted.replace(
      /\b(console|window|document|Array|Object|String|Number|Boolean|Promise|Map|Set|JSON|Math|Date|RegExp|Error|setTimeout|setInterval|fetch|require)\b/g,
      '<span class="hl-builtin">$1</span>',
    );
  } else if (["sql", "mysql", "postgresql", "postgres"].includes(language)) {
    highlighted = highlighted.replace(sqlKeywords, '<span class="hl-keyword">$&</span>');
  } else if (["bash", "sh", "shell", "zsh"].includes(language)) {
    highlighted = highlighted.replace(bashKeywords, '<span class="hl-keyword">$1</span>');
    highlighted = highlighted.replace(
      /(\$\w+|\$\{[^}]+\})/g,
      '<span class="hl-variable">$1</span>',
    );
  } else if (["json", "jsonc"].includes(language)) {
    highlighted = highlighted.replace(jsonKeywords, '<span class="hl-keyword">$1</span>');
  } else {
    highlighted = highlighted.replace(jsKeywords, '<span class="hl-keyword">$1</span>');
  }

  highlighted = highlighted.replace(/(\/\/.*|#[^\n]*)/g, '<span class="hl-comment">$1</span>');
  highlighted = highlighted.replace(
    /(&quot;[^&]*?&quot;|'[^']*?')/g,
    '<span class="hl-string">$1</span>',
  );
  highlighted = highlighted.replace(
    /\bf(&quot;[^&]*?&quot;|'[^']*?')/g,
    '<span class="hl-string">f$1</span>',
  );
  highlighted = highlighted.replace(
    /\b(\d+\.?\d*(?:e[+-]?\d+)?|0x[\da-fA-F]+|0b[01]+|0o[0-7]+)\b/g,
    '<span class="hl-number">$1</span>',
  );
  highlighted = highlighted.replace(
    /\b([a-zA-Z_]\w*)(?=\s*\()/g,
    '<span class="hl-function">$1</span>',
  );

  return highlighted;
}

function formatMarkdownText(text: string): string {
  if (!text) return "";

  const inlineCodePlaceholders: string[] = [];

  let html = escapeHtml(text).replace(/\n{2,}/g, "\n\n");

  // Extract inline code to placeholders BEFORE emphasis parsing
  html = html.replace(/`([^`]+)`/g, (_match, code: string) => {
    return createPlaceholder(`<code>${code}</code>`, inlineCodePlaceholders);
  });

  // Extract {_{key}_} private data placeholders BEFORE emphasis parsing
  // so underscores inside them don't get consumed by italic/bold rules
  html = html.replace(/\{_\{(?:&quot;)?([^}"]+?)(?:&quot;)?\}_\}/g, (_match, key: string) => {
    return createPlaceholder(
      `<span class="private-data-badge">\u{1F6E1} ${key}</span>`,
      inlineCodePlaceholders,
    );
  });

  html = renderTables(html);

  html = html
    .replace(/~~([^~]+)~~/g, "<del>$1</del>")
    .replace(/\*\*([^*]+)\*\*/g, "<strong>$1</strong>")
    .replace(/\*(?!\s)([^*\n]*?\S)\*/g, "<em>$1</em>")
    .replace(/^######\s+(.+)$/gm, "<h6>$1</h6>")
    .replace(/^#####\s+(.+)$/gm, "<h5>$1</h5>")
    .replace(/^####\s+(.+)$/gm, "<h4>$1</h4>")
    .replace(/^###\s+(.+)$/gm, "<h3>$1</h3>")
    .replace(/^##\s+(.+)$/gm, "<h2>$1</h2>")
    .replace(/^#\s+(.+)$/gm, "<h1>$1</h1>")
    .replace(/^>\s+(.+)$/gm, "<blockquote>$1</blockquote>")
    .replace(/^[-*]\s+(.+)$/gm, '<li data-list="ul">$1</li>')
    .replace(/^\d+\.\s+(.+)$/gm, '<li data-list="ol">$1</li>')
    .replace(/^---+$/gm, "<hr>");

  html = replaceUnderscoreDelimited(html, "__", "strong");
  html = replaceUnderscoreDelimited(html, "_", "em");

  html = html
    .replace(/\[([^\]]+)\]\(([^)]+)\)/g, renderMarkdownLink)
    .replace(/\n\n/g, "</p><p>")
    .replace(/\n/g, "<br>");

  if (!html.startsWith("<")) {
    html = `<p>${html}</p>`;
  }

  html = html.replace(
    /(<li data-list="ul">.*?<\/li>)+/g,
    (match) => `<ul>${match.replace(/ data-list="ul"/g, "")}</ul>`,
  );
  html = html.replace(
    /(<li data-list="ol">.*?<\/li>)+/g,
    (match) => `<ol>${match.replace(/ data-list="ol"/g, "")}</ol>`,
  );

  return restorePlaceholders(html, inlineCodePlaceholders);
}

export function parseMarkdown(text: string): string {
  if (!text) return "";

  const normalized = text.replace(/\r\n?/g, "\n");
  const codeBlockRegex = /```([^\n`]*)\n([\s\S]*?)```/g;
  const segments: { type: "text" | "code"; value: string }[] = [];
  let lastIndex = 0;
  let match: RegExpExecArray | null;

  while ((match = codeBlockRegex.exec(normalized)) !== null) {
    const [full, rawLang, code] = match;
    const before = normalized.slice(lastIndex, match.index);
    if (before) {
      segments.push({ type: "text", value: before });
    }

    const lang = rawLang.trim();
    const langClass = lang ? ` class="language-${lang}"` : "";
    const langLabel = lang ? ` data-lang="${lang.toUpperCase()}"` : "";
    const cleanedCode = code.replace(/\n$/, "");
    const highlightedCode = highlightCode(cleanedCode, lang);
    const htmlBlock = `<div class="code-block-wrapper" data-code="${escapeHtml(cleanedCode).replace(/"/g, "&quot;")}"><pre${langLabel}><code${langClass}>${highlightedCode}</code></pre></div>`;
    segments.push({ type: "code", value: htmlBlock });

    lastIndex = match.index + full.length;
  }

  if (lastIndex < normalized.length) {
    segments.push({ type: "text", value: normalized.slice(lastIndex) });
  }

  return segments
    .map((segment) => (segment.type === "code" ? segment.value : formatMarkdownText(segment.value)))
    .join("");
}
