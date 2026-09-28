/* Lockup da marca: símbolo + "NERIAH / DATA".
 *
 * O símbolo é um PNG com fundo transparente, então o mesmo arquivo serve em
 * superfície clara e escura. O nome é texto — assim ele acompanha a cor da
 * tinta do tema em vez de ficar preso a um branco de imagem. */

export default function Marca({ tamanho = 20, comNome = true, className = "" }) {
  return (
    <span className={`marca-lockup ${className}`} style={{ fontSize: tamanho }}>
      <img src="/neriah-simbolo.png" alt="Neriah Data" />
      {comNome && (
        <span>
          <span className="marca-nome">NERIAH</span>
          <span className="marca-sub">DATA</span>
        </span>
      )}
    </span>
  );
}
