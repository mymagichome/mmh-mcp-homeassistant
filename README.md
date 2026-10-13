# MMH MCP — integração para Home Assistant

Servidor [MCP](https://modelcontextprotocol.io) que roda dentro do Home Assistant, em `POST /api/mmh_mcp`. É o lado "casa" da plataforma MCP da **My Magic Home**: o gateway da MMH (Cloudflare) chama esta integração em cada site para que o Claude consulte e opere o HA, com login, permissões por pessoa e auditoria.

## Instalação (HACS)

1. No HA, abra **HACS → ⋮ → Repositórios personalizados**.
2. Cole `https://github.com/mymagichome/mmh-mcp-homeassistant` e escolha a categoria **Integração**.
3. Procure **MMH MCP** no HACS, clique em **Baixar** e **reinicie o Home Assistant**.
4. Vá em **Configurações → Dispositivos e serviços → Adicionar integração → MMH MCP**. Os padrões recomendados:
   - escrita: ligada;
   - destrutivo: desligado;
   - disparo de eventos: desligado.

As atualizações aparecem no HACS como qualquer outra integração.

## Preparar o site para o gateway MMH

1. **Crie o usuário do gateway.** Em Configurações → Pessoas, crie **MMH Gateway** (usuário `mmh-gateway`), marcado como **administrador** e **pode fazer login**.
2. **Gere o token.** Entre com esse usuário numa janela anônima e, em **Perfil → Segurança**, crie um **token de longa duração**.
3. **Cadastre o site no gateway.** No computador de administração:
   ```bash
   npm run admin -- site add <slug> --name "Nome do cliente" \
     --url https://<cliente>.mymagichome.com.br --access-id <client-id>.access
   npm run admin -- site test <slug>
   ```

O endpoint `/api/mmh_mcp` de todos os `*.mymagichome.com.br` já é protegido pelo Cloudflare Access (token de serviço `mmh-gateway`). O resto do HA (dashboards, app) não é afetado.

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

Cada tool publica em `_meta["br.com.mymagichome/permissions"]` a sua classe (leitura, escrita ou destrutiva) e quais operações exigem admin. É isso que o gateway usa para aplicar os papéis viewer/operator/admin.

As opções da integração (`allow_write`, `allow_destructive`, `allow_fire_event`) continuam valendo como uma segunda trava dentro do HA.

## Origem e licença

Fork do [czechbol/hass-mcp](https://github.com/czechbol/hass-mcp) 2.2.2, sob licença MIT (veja `LICENSE`). Mudanças:

- **Identidade própria:** domínio `mmh_mcp`, nome "MMH MCP" e endpoint `/api/mmh_mcp`. Pode conviver com o hass-mcp original.
- **Classificação de permissão por tool** em `_meta`, para o gateway.

Para incorporar uma versão nova do upstream, copie o código novo, troque `hass_mcp` → `mmh_mcp` e preserve:
- `registry.py`: `permissions()` e `_meta`;
- `const.py`: `META_PERMISSIONS_KEY` e as versões.

## Publicar uma versão nova

1. Atualize `version` em `custom_components/mmh_mcp/manifest.json` e `SERVER_VERSION` em `const.py`.
2. Faça o commit e crie a tag (`git tag v1.0.1 && git push --tags`).
3. No GitHub, abra **Releases → Draft a new release**, escolha a tag e publique. O HACS mostra a atualização nos HA.

## Desenvolvimento

```bash
pip install -r requirements_test.txt   # Python 3.13+
pytest
ruff check . && ruff format --check .
```
