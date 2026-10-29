// Shell sem dados privados. Login e autorização reais são o próximo incremento da SPEC-0033.
export const dynamic = "force-dynamic";

export default function Home() {
  return (
    <main className="access-shell">
      <div className="brand">LottoBrain</div>
      <section className="access-card" aria-labelledby="access-title">
        <span className="eyebrow">ESPAÇO PRIVADO</span>
        <h1 id="access-title">Seu espaço de análise está sendo preparado.</h1>
        <p>A entrada será liberada após a configuração do acesso e a aprovação do administrador.</p>
        <p className="status">Nenhum resultado ou dado privado está disponível nesta página.</p>
      </section>
    </main>
  );
}
