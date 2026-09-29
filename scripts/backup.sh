#!/bin/sh
# Backup diário do banco e das planilhas enviadas.
#
# Roda como serviço: dorme até a próxima madrugada e repete. Guarda dump do
# Postgres e tar das planilhas — as duas metades são necessárias, porque o banco
# tem o resultado das análises e o disco tem os arquivos originais do cliente.
set -eu

RETENCAO="${RETENCAO_DIAS:-14}"
DESTINO=/backups

fazer_backup() {
	data=$(date +%Y-%m-%d_%H%M)
	echo "[$(date -Iseconds)] iniciando backup $data"

	if pg_dump --format=custom --file="$DESTINO/banco_$data.dump"; then
		echo "  banco: $(du -h "$DESTINO/banco_$data.dump" | cut -f1)"
	else
		echo "  ERRO no pg_dump — backup do banco não foi gerado" >&2
		return 1
	fi

	if [ -d /dados_clientes ]; then
		tar -czf "$DESTINO/planilhas_$data.tar.gz" -C /dados_clientes . 2>/dev/null || true
		echo "  planilhas: $(du -h "$DESTINO/planilhas_$data.tar.gz" | cut -f1)"
	fi

	# Só remove os antigos depois que o novo existe, para nunca ficar sem nenhum.
	find "$DESTINO" -name 'banco_*.dump' -mtime "+$RETENCAO" -delete
	find "$DESTINO" -name 'planilhas_*.tar.gz' -mtime "+$RETENCAO" -delete
	echo "[$(date -Iseconds)] backup concluído (retenção: $RETENCAO dias)"
}

# Um backup ao subir, para nunca existir um dia sem cópia.
fazer_backup || echo "primeiro backup falhou, tentando de novo no horário" >&2

while true; do
	agora=$(date +%s)
	# próxima 03:15 local
	proxima=$(date -d 'tomorrow 03:15' +%s 2>/dev/null || echo $((agora + 86400)))
	sono=$((proxima - agora))
	[ "$sono" -le 0 ] && sono=86400
	sleep "$sono"
	fazer_backup || echo "backup falhou; tentará amanhã" >&2
done
