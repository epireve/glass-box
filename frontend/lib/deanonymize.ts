/**
 * Deanonymization utility for restoring original PII values from placeholders.
 * Handles the "Glass Box" reveal effect where anonymized LLM responses are
 * transformed back to show original values.
 */

/**
 * Replace all PII placeholders with their original values.
 *
 * @param text - The anonymized text containing placeholders like <PERSON_1>
 * @param mapping - The mapping of placeholders to original values
 * @returns Text with placeholders replaced by original values
 *
 * @example
 * ```ts
 * const text = "Dear <PERSON_1>, your salary of <SALARY_1> has been approved.";
 * const mapping = {
 *   "<PERSON_1>": "Alice Chen",
 *   "<SALARY_1>": "$145,000"
 * };
 * const result = deanonymize(text, mapping);
 * // "Dear Alice Chen, your salary of $145,000 has been approved."
 * ```
 */
export function deanonymize(
  text: string,
  mapping: Record<string, string>
): string {
  if (!text || !mapping || Object.keys(mapping).length === 0) {
    return text;
  }

  let result = text;

  // Sort placeholders by length (longest first) to avoid partial replacements
  const sortedPlaceholders = Object.keys(mapping).sort(
    (a, b) => b.length - a.length
  );

  for (const placeholder of sortedPlaceholders) {
    const original = mapping[placeholder];
    // Use global replace to handle multiple occurrences
    result = result.split(placeholder).join(original);
  }

  return result;
}

/**
 * Check if text contains any PII placeholders.
 *
 * @param text - The text to check
 * @returns True if text contains placeholders like <ENTITY_N>
 */
export function containsPlaceholders(text: string): boolean {
  return /<[A-Z_]+_\d+>/.test(text);
}

/**
 * Extract all placeholders from text.
 *
 * @param text - The text to search
 * @returns Array of unique placeholder strings found
 */
export function extractPlaceholders(text: string): string[] {
  const matches = text.match(/<[A-Z_]+_\d+>/g);
  return matches ? [...new Set(matches)] : [];
}

/**
 * Get entity type from a placeholder.
 *
 * @param placeholder - The placeholder string like <PERSON_1>
 * @returns The entity type like "PERSON" or null if invalid
 */
export function getEntityType(placeholder: string): string | null {
  const match = placeholder.match(/<([A-Z_]+)_\d+>/);
  return match ? match[1] : null;
}

/**
 * Create a highlighted version of text where placeholders are wrapped
 * with special markers for UI highlighting.
 *
 * @param text - The text containing placeholders
 * @returns Text with placeholders wrapped for highlighting
 */
export function highlightPlaceholders(text: string): string {
  return text.replace(
    /<([A-Z_]+)_(\d+)>/g,
    '<span class="pii-placeholder" data-entity="$1" data-index="$2">&lt;$1_$2&gt;</span>'
  );
}

/**
 * Progressively reveal deanonymized text with animation support.
 * Returns an array of steps for animated reveal.
 *
 * @param text - The anonymized text
 * @param mapping - The placeholder to original mapping
 * @returns Array of text states from fully anonymized to fully revealed
 */
export function getRevealSteps(
  text: string,
  mapping: Record<string, string>
): string[] {
  const steps: string[] = [text];
  let current = text;

  // Get placeholders in order of appearance
  const placeholders = extractPlaceholders(text);

  for (const placeholder of placeholders) {
    if (mapping[placeholder]) {
      current = current.replace(placeholder, mapping[placeholder]);
      steps.push(current);
    }
  }

  return steps;
}

/**
 * Calculate the "anonymization score" - percentage of text that was PII.
 *
 * @param originalText - The original text before anonymization
 * @param mapping - The placeholder to original mapping
 * @returns Score from 0-100 representing percentage of PII content
 */
export function calculateAnonymizationScore(
  originalText: string,
  mapping: Record<string, string>
): number {
  if (!originalText || !mapping) return 0;

  let piiCharCount = 0;
  for (const original of Object.values(mapping)) {
    piiCharCount += original.length;
  }

  return Math.round((piiCharCount / originalText.length) * 100);
}
