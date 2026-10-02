/* `catch (e)` entrega `unknown`, e com razão: dá para lançar qualquer coisa em
 * JavaScript. O código assumia `.message` em todo lugar, o que quebraria se
 * alguém lançasse uma string. Este é o único ponto que decide a mensagem. */
export function mensagemDoErro(e: unknown): string {
  if (e instanceof Error) return e.message;
  if (typeof e === "string") return e;
  return "Algo deu errado. Tente de novo.";
}
