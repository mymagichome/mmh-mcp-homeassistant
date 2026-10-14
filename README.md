# MMH MCP — integração para Home Assistant

Servidor [MCP](https://modelcontextprotocol.io) que roda dentro do Home Assistant, em `POST /api/mmh_mcp`. É o lado "casa" da plataforma MCP da **My Magic Home**: o gateway da MMH (Cloudflare) chama esta integração em cada site para que o Claude consulte e opere o HA, com login, permissões por pessoa e auditoria.

## Instalação (HACS)

1. No HA, abra **HACS → ⋮ → Repositórios personalizados**.
2. Cole `https://github.com/mymagichome/mmh-mcp-homeassistant` e escolha a categoria **Integração**.
3. Procure **MMH MCP** no HACS, clique em **Baixar** e **reinicie o Home Assistant**.
4. Vá em **Configurações → Dispositivos e serviços → Adicionar integração → MMH MCP**. Nas permissões das tools, os padrões recomendados:
   - escrita: ligada;
   - destrutivo: desligado;
   - disparo de eventos: desligado.

As atualizações aparecem no HACS como qualquer outra integração.

## Conectar ao gateway MMH

1. **Gerar o código.** No painel do gateway (`https://mcp.mymagichome.com.br/admin`), gere um **código de pareamento**. Ele vale uma vez, por 24 horas.
2. **Colar o código no HA.** Ao adicionar a integração, na etapa **Conectar ao gateway MMH**, cole o código e confira o identificador, o nome e o endereço público do site. Eles vêm preenchidos a partir do `external_url` do HA.
3. **Pronto.** A integração cria sozinha o usuário **MMH Gateway** (administrador, sem login de interface) e um token de longa duração, e envia tudo ao gateway. O gateway testa a conexão antes de aceitar:
   - se der certo, o site já está disponível no Claude;
   - se der errado, o motivo aparece na tela e nada fica cadastrado.

**Conectar depois ou reconectar:** vá em MMH MCP → **Configurar** → **Conectar / reconectar ao gateway MMH**. Para reconectar um site existente, gere no painel um código específico para ele. Cada novo pareamento cria um token novo e revoga o anterior.

**Remover a integração** apaga também o usuário MMH Gateway e todos os tokens dele.

O endpoint `/api/mmh_mcp` de todos os `*.mymagichome.com.br` é protegido pelo Cloudflare Access (token de serviço do gateway). O resto do HA (dashboards, app) não é afetado.

## Uso direto, sem o gateway

Clientes MCP que aceitam cabeçalho, como o Claude Desktop e o Claude Code, podem chamar o endpoint direto com um token do HA:

```bash
claude mcp add --transport http ha-casa https://<seu-ha>/api/mmh_mcp --header "Authorization: Bearer <token>"
```

## O que a integração expõe

São cerca de 30 tools `ha_*`, entre elas:
- estados, histórico e estatísticas;
- chamada de serviços;
- automações, scripts, cenas e blueprints;
- dashboards (Lovelace) e helpers;
- registry, integrações e config flows;
- backups, logs, traces e templates;
- HACS e Assist.

As traduções da interface estão em português e inglês.

Cada tool publica em `_meta["br.com.mymagichome/permissions"]` a sua classe (leitura, escrita ou destrutiva) e quais operações exigem admin. É isso que o gateway usa para aplicar os papéis viewer/operator/admin.

As opções da integração (`allow_write`, `allow_destructive`, `allow_fire_event`) continuam valendo como uma segunda trava dentro do HA.

## Origem e licença

Fork do [czechbol/hass-mcp](https://github.com/czechbol/hass-mcp) 2.2.2, sob licença MIT (veja `LICENSE`). Mudanças:

- **Identidade própria:** domínio `mmh_mcp`, nome "MMH MCP" e endpoint `/api/mmh_mcp`. Pode conviver com o hass-mcp original.
- **Classificação de permissão por tool** em `_meta`, para o gateway.
- **Pareamento com o gateway MMH** pelo fluxo de configuração (`gateway_link.py`).
- **Registro único da view:** o recarregamento da integração não duplica a rota. Sem configuração carregada, o endpoint responde 503.

Para incorporar uma versão nova do upstream, copie o código novo, troque `hass_mcp` → `mmh_mcp` e preserve:
- `registry.py`: `permissions()` e `_meta`;
- `const.py`: `META_PERMISSIONS_KEY` e as versões.

## Publicar uma versão nova

1. Atualize `version` em `custom_components/mmh_mcp/manifest.json` e `SERVER_VERSION` em `const.py`.
2. Faça o commit e envie com a tag (`git tag v1.2.0 && git push origin main v1.2.0`). No repositório MyMagicHome, o `mmh-mcp/scripts/publicar-integracao.sh` faz isso.
3. O GitHub Actions cria a release sozinho (workflow *Release*), e o HACS mostra a atualização nos HA.

Sem como enviar a tag (numa sessão do Claude, por exemplo), envie só o commit para a `main` e rode o workflow *Release* à mão: ele cria a tag e a release com a versão do manifest.

## Desenvolvimento

```bash
pip install -r requirements_test.txt   # Python 3.13+
pytest
ruff check . && ruff format --check .
```
