import streamlit as st
import google.generativeai as genai
from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from googleapiclient.http import MediaIoBaseDownload
import io
import re

# --- Configurações Iniciais ---
# Substitua pela sua chave da API Google Gemini
# Você pode armazenar isso de forma segura usando st.secrets no Streamlit Cloud
# Saiba mais: https://docs.streamlit.io/deploy/streamlit-cloud/quickstart#set-up-secrets
GOOGLE_API_KEY = st.secrets["GOOGLE_API_KEY"]
genai.configure(api_key=GOOGLE_API_KEY)
model = genai.GenerativeModel('gemini-2.0-flash')

# Configurações para a API do Google Drive e Docs
# Para autenticação em Streamlit, um service account é recomendado.
# Crie um arquivo JSON com as credenciais do seu service account e armazene-o em st.secrets
# Ex: st.secrets["gcp_service_account"] = {...}
try:
    creds_info = st.secrets["gcp_service_account"]
    creds = service_account.Credentials.from_service_account_info(creds_info)
    drive_service = build('drive', 'v3', credentials=creds)
    docs_service = build('docs', 'v1', credentials=creds)
except Exception as e:
    st.error(f"Erro ao carregar credenciais do Google Cloud: {e}")
    st.info("Certifique-se de que suas credenciais de service account estão configuradas corretamente no `secrets.toml`.")
    st.stop()


# --- Funções Utilitárias ---

def display_welcome_message():
    welcome_text = """
    <div style='background-color:#f0f2f6; padding: 20px; border-radius: 10px;'>
        <h2 style='color:#FF4B4B; text-align:center;'>🐉 MindForge - Assistente Criativo para Construção de Mundos 🐦‍🔥</h2>
        <p style='font-size:1.1em; text-align:center;'>Bem-vindo ao MindForge, o seu assistente interativo para criação de mundos!</p>
        <p><strong>O que eu posso fazer?</strong></p>
        <p>Vou te ajudar a criar e desenvolver qualquer aspecto do seu mundo. 🗺️ Juntos podemos criar continentes, raças, personagens, criaturas, artefatos, tecnologias e muito mais! O limite é a sua imaginação!</p>
        <p>Ao interagir comigo, você pode criar ou editar um arquivo existente em seu Google Drive.</p>
        <p style='text-align:center; font-weight:bold;'>Vamos começar?</p>
    </div>
    """
    st.markdown(welcome_text, unsafe_allow_html=True)

def read_google_doc_content(file_id):
    try:
        request = drive_service.files().export_media(fileId=file_id, mimeType='text/plain')
        fh = io.BytesIO()
        downloader = MediaIoBaseDownload(fh, request)
        done = False
        while done is False:
            status, done = downloader.next_chunk()
        fh.seek(0)
        content_text = fh.read().decode('utf-8')
        return content_text if content_text else ""
    except Exception as e:
        st.error(f"Erro ao ler conteúdo do documento: {e}")
        return ""

def clean_nonstructural_markdown(text):
    text = re.sub(r'\*\*(.*?)\*\*', r'\1', text)
    text = re.sub(r'\*(.*?)\*', r'\1', text)
    return text

def update_google_doc(file_id, new_content_markdown, is_initial_creation=False):
    try:
        if not is_initial_creation:
            document = docs_service.documents().get(documentId=file_id).execute()
            end_index = document['body']['content'][-1]['endIndex'] - 1
        else:
            end_index = 1

        cleaned_content = clean_nonstructural_markdown(new_content_markdown)
        requests = convert_markdown_to_docs_requests(cleaned_content, end_index)

        if requests:
            docs_service.documents().batchUpdate(documentId=file_id, body={'requests': requests}).execute()
        return True
    except Exception as e:
        st.error(f"Erro ao atualizar documento: {e}")
        return False

def convert_markdown_to_docs_requests(markdown_text, start_index):
    requests = []
    current_idx = start_index

    if start_index > 1:
        requests.append({
            'insertText': {
                'location': {'index': current_idx},
                'text': '\n\n---\n\n'
            }
        })
        current_idx += len('\n\n---\n\n')

    lines = markdown_text.split('\n')
    for line in lines:
        stripped_line = line.strip()
        if not stripped_line:
            requests.append({
                'insertText': {
                    'location': {'index': current_idx},
                    'text': '\n'
                }
            })
            current_idx += 1
            continue
        if stripped_line.startswith('### '):
            text = stripped_line[4:].strip()
            insert_start_idx = current_idx
            requests.append({'insertText': {'location': {'index': current_idx}, 'text': text + '\n'}})
            current_idx += len(text) + 1
            requests.append({
                'updateParagraphStyle': {
                    'range': {'startIndex': insert_start_idx, 'endIndex': current_idx},
                    'paragraphStyle': {'namedStyleType': 'HEADING_3'},
                    'fields': 'namedStyleType'
                }
            })
        elif stripped_line.startswith('## '):
            text = stripped_line[3:].strip()
            insert_start_idx = current_idx
            requests.append({'insertText': {'location': {'index': current_idx}, 'text': text + '\n'}})
            current_idx += len(text) + 1
            requests.append({
                'updateParagraphStyle': {
                    'range': {'startIndex': insert_start_idx, 'endIndex': current_idx},
                    'paragraphStyle': {'namedStyleType': 'HEADING_2'},
                    'fields': 'namedStyleType'
                }
            })
        elif stripped_line.startswith('# '):
            text = stripped_line[2:].strip()
            insert_start_idx = current_idx
            requests.append({'insertText': {'location': {'index': current_idx}, 'text': text + '\n'}})
            current_idx += len(text) + 1
            requests.append({
                'updateParagraphStyle': {
                    'range': {'startIndex': insert_start_idx, 'endIndex': current_idx},
                    'paragraphStyle': {'namedStyleType': 'HEADING_1'},
                    'fields': 'namedStyleType'
                }
            })
        elif stripped_line.startswith('* '):
            text = stripped_line[2:].strip()
            insert_start_idx = current_idx
            requests.append({'insertText': {'location': {'index': current_idx}, 'text': text + '\n'}})
            current_idx += len(text) + 1
            requests.append({
                'createParagraphBullets': {
                    'range': {'startIndex': insert_start_idx, 'endIndex': current_idx},
                    'bulletPreset': 'BULLET_DISC_CIRCLE_SQUARE'
                }
            })
        else:
            # Texto comum
            requests.append({
                'insertText': {
                    'location': {'index': current_idx},
                    'text': stripped_line + '\n'
                }
            })
            current_idx += len(stripped_line) + 1
    return requests


def generate_creative_content(request, context):
    instruction_prompt = f"""
    Você é um assistente criativo de construção de mundos. Sua tarefa é ajudar o usuário a desenvolver seu mundo de fictício, seja ele de fantasia, ficção científica, terror ou outros gêneros.
    Considere o seguinte contexto do mundo já criado:
    ---
    {context}
    ---

    Com base no pedido do usuário: "{request}", gere uma descrição rica, detalhada e criativa. Sempre que possível, incite a criatividade do usuário, visando enriquecer o mundo que ele está desenvolvendo ou lapidar uma ideia já existente. **Sua formatação deve ser hierárquica e apropriada para um compêndio ou enciclopédia, começando com títulos de nível 1.**

    Utilize os seguintes padrões de formatação Markdown para que sejam corretamente interpretados no Google Docs:

    * **Para Títulos de Seção PRINCIPAIS (como 'Título 1' no Docs):** Use `# ` (ex: `# História Antiga`). Use para as grandes divisões do seu mundo.
    * **Para Subseções (como 'Título 2' no Docs):** Use `## ` (ex: `## Geologia`).
    * **Para Sub-subseções (como 'Título 3' no Docs):** Use `### ` (ex: `### Cavernas de Cristal`).
    * **Para itens de lista:** Use `* ` (ex: `* Criaturas Noturnas`).
    * **Para destacar texto (negrito):** Use `**texto em negrito**`. **Utilize negrito para maior hierarquização do texto dentro de parágrafos ou como sub-sub-sub-seções, quando 'Título 3' não for suficiente.**

    **Importante:** NÃO utilize formatação específica para "Título Principal do Documento" ou "Subtítulo do Documento" no conteúdo gerado. Use `TÍTULO 1` (`#`) como o nível mais alto de seção para o conteúdo que você criar. Mantenha a informação bem organizada com quebras de linha e parágrafos claros. A resposta deve ser útil e inspiradora para o desenvolvimento do mundo.
    Se o pedido for genérico e não houver contexto, crie uma ideia original.
    Se o pedido for para expandir algo, use o contexto fornecido.
    """

    generation_config = genai.types.GenerationConfig(max_output_tokens=2000)
    safety_settings = [
        {"category": "HARM_CATEGORY_HARASSMENT", "threshold": "BLOCK_MEDIUM_AND_ABOVE"},
        {"category": "HARM_CATEGORY_HATE_SPEECH", "threshold": "BLOCK_MEDIUM_AND_ABOVE"},
        {"category": "HARM_CATEGORY_SEXUALLY_EXPLICIT", "threshold": "BLOCK_MEDIUM_AND_ABOVE"},
        {"category": "HARM_CATEGORY_DANGEROUS_CONTENT", "threshold": "BLOCK_MEDIUM_AND_ABOVE"},
    ]
    try:
        response = model.generate_content(
            instruction_prompt,
            generation_config=generation_config,
            safety_settings=safety_settings
            )
        return response.text if response.parts else "Desculpe, não consegui gerar resposta."
    except Exception as e:
        st.error(f"Erro na IA: {e}")
        return "Erro na IA."

# --- Lógica da Aplicação Streamlit ---

def main():
    if 'document_id' not in st.session_state:
        st.session_state.document_id = None
        st.session_state.document_title = "Meu Compêndio de Mundos Criativos"
        st.session_state.document_link = None
        st.session_state.current_world_context = ""
        st.session_state.app_state = "welcome" # "welcome", "select_doc", "main_interface"

    if st.session_state.app_state == "welcome":
        display_welcome_message()
        if st.button("Começar"):
            st.session_state.app_state = "select_doc"
            st.rerun()

    elif st.session_state.app_state == "select_doc":
        st.markdown("<div style='font-size:1.1em; margin-bottom: 15px;'><b>Crie um novo compêndio ou pesquise por um já existente no seu Google Drive:</b></div>", unsafe_allow_html=True)

        with st.form("create_new_doc_form"):
            name_text = st.text_input("Crie um novo compêndio:", placeholder="Ex: Crônicas Fantásticas")
            submitted_create = st.form_submit_button("Criar novo compêndio")
            if submitted_create:
                doc_name = name_text.strip() or "Meu Compêndio de Mundos Criativos"
                file_metadata = {'name': doc_name, 'mimeType': 'application/vnd.google-apps.document'}
                try:
                    file = drive_service.files().create(body=file_metadata, fields='id, webViewLink, name').execute()
                    st.session_state.document_id = file.get('id')
                    st.session_state.document_link = file.get('webViewLink')
                    st.session_state.document_title = file.get('name')
                    st.session_state.current_world_context = f"# {st.session_state.document_title}\n\n*Este compêndio foi iniciado com o Assistente Interativo de Criação de Mundos.*\n\n"
                    update_google_doc(st.session_state.document_id, st.session_state.current_world_context, is_initial_creation=True)
                    st.success(f"Compêndio '{st.session_state.document_title}' criado com sucesso!")
                    st.session_state.app_state = "main_interface"
                    st.rerun()
                except Exception as e:
                    st.error(f"Erro ao criar documento: {e}")

        st.markdown("---") # Separador visual

        with st.form("search_existing_doc_form"):
            search_text = st.text_input("Buscar compêndio:", placeholder="Nome ou parte do nome")
            submitted_search = st.form_submit_button("Buscar")

            if submitted_search:
                query = f"name contains '{search_text}' and mimeType='application/vnd.google-apps.document' and trashed=false"
                try:
                    results = drive_service.files().list(q=query, spaces='drive', pageSize=10, fields='files(id, name, webViewLink)').execute()
                    items = results.get('files', [])
                    if items:
                        options = {item.get('name'): item for item in items}
                        st.session_state.found_docs = options
                        st.session_state.selected_doc_name = None
                    else:
                        st.session_state.found_docs = {}
                        st.session_state.selected_doc_name = None
                        st.info("Nenhum documento encontrado.")
                except Exception as e:
                    st.error(f"Erro ao buscar documentos: {e}")

        if 'found_docs' in st.session_state and st.session_state.found_docs:
            selected_name = st.selectbox("Documentos encontrados:", list(st.session_state.found_docs.keys()))
            if selected_name:
                st.session_state.selected_doc_name = selected_name
                if st.button("Confirmar seleção"):
                    selected_file = st.session_state.found_docs[st.session_state.selected_doc_name]
                    st.session_state.document_id = selected_file['id']
                    st.session_state.document_title = selected_file['name']
                    st.session_state.document_link = selected_file['webViewLink']
                    st.session_state.current_world_context = read_google_doc_content(st.session_state.document_id)
                    st.success(f"Compêndio '{st.session_state.document_title}' selecionado!")
                    st.session_state.app_state = "main_interface"
                    st.rerun()


    elif st.session_state.app_state == "main_interface":
        st.markdown(f"<h3>Compêndio selecionado: <b>{st.session_state.document_title}</b></h3>", unsafe_allow_html=True)
        st.link_button("Acessar compêndio no Google Drive", st.session_state.document_link)

        user_input = st.text_area(
            "O que você tem em mente? Conta aí 😉",
            placeholder="Descreva sua ideia ou clique em Gerar para uma sugestão surpresa!",
            height=150
        )

        col1, col2 = st.columns([0.2, 0.8])
        with col1:
            gerar_btn = st.button("Gerar Ideia", type="primary")
        with col2:
            if st.session_state.document_link:
                st.markdown(f"<span style='font-size:0.9em;'>Seu compêndio: <a href='{st.session_state.document_link}' target='_blank'>Abrir no Drive</a></span>", unsafe_allow_html=True)


        if gerar_btn:
            if user_input.strip() == "":
                st.warning("Por favor, descreva sua ideia ou deixe em branco para uma sugestão surpresa.")
            else:
                st.info("Gerando...")
                ai_text = generate_creative_content(user_input, st.session_state.current_world_context)
                st.session_state.last_ai_text = ai_text # Armazena para confirmar/regenerar
                st.markdown("---")
                st.markdown("### ✨ Minha Sugestão para Você ✨")
                st.markdown(ai_text)
                st.markdown("---")

                col_confirm, col_regenerate = st.columns(2)
                with col_confirm:
                    if st.button("Confirmar e Salvar no Compêndio", type="success"):
                        with st.spinner("Salvando..."):
                            ok = update_google_doc(st.session_state.document_id, st.session_state.last_ai_text)
                            if ok:
                                st.success("O seu compêndio foi atualizado com sucesso!")
                                # Atualiza o contexto global após salvar
                                st.session_state.current_world_context = read_google_doc_content(st.session_state.document_id)
                            else:
                                st.error("Erro ao salvar.")
                with col_regenerate:
                    if st.button("Gerar Outra Ideia", type="warning"):
                        st.info("Gerando uma nova ideia...")
                        # Ao regenerar, usa o último input do usuário
                        ai_text = generate_creative_content(user_input, st.session_state.current_world_context)
                        st.session_state.last_ai_text = ai_text
                        st.markdown("---")
                        st.markdown("### ✨ Minha Nova Sugestão ✨")
                        st.markdown(ai_text)
                        st.markdown("---")
                        st.warning("Nova sugestão gerada. Clique em 'Confirmar e Salvar' para adicionar.")


if __name__ == "__main__":
    main()