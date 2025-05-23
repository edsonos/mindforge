# -*- coding: utf-8 -*-
"""MindForge

Automatically generated by Colab.

Original file is located at
    https://colab.research.google.com/drive/10JNBIBgtV2Q6D1R-CM6aIPQ5DW1xsz9w

# 🐉 MindForge - Assistente Criativo para Construção de Mundos 🐦‍🔥

MindForge é um assistente interativo que utiliza IA generativa para ajudar criadores, escritores e entusiastas a desenvolverem mundos de ficção ricos e detalhados diretamente no Google Drive.

Projeto desenvolvido durante a Imersão IA Alura + Google DeepMind.

Como usar:
1. Execute as células abaixo e siga as instruções que aparecerão.
2. Autentique sua conta Google quando solicitado.
3. Crie um compêndio novo ou selecione um existente.
4. Descreva sua ideia ou peça sugestões e salve automaticamente direto no seu Drive!

#Configurações Iniciais 🛠️
"""

# Instalações necessárias
!pip install -q google-api-python-client google-auth-httplib2 google-auth-oauthlib google-generativeai Markdown ipywidgets

# Importações necessárias
from google.colab import auth, userdata
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from googleapiclient.http import MediaIoBaseDownload
import google.generativeai as genai
from IPython.display import display, Markdown, clear_output, Javascript
import io, google.auth, re
import ipywidgets as widgets

# Configuração
SCOPES = ['https://www.googleapis.com/auth/drive', 'https://www.googleapis.com/auth/documents']
GOOGLE_API_KEY = userdata.get('GOOGLE_API_KEY')
genai.configure(api_key=GOOGLE_API_KEY)
model = genai.GenerativeModel('gemini-2.0-flash')

auth.authenticate_user()
creds, project = google.auth.default(scopes=SCOPES)
drive_service = build('drive', 'v3', credentials=creds)
docs_service = build('docs', 'v1', credentials=creds)

document_id = None
document_title = "Meu Compêndio de Mundos Criativos"
document_link = None
current_world_context = ""

"""#Ativação de infraestrutura ✅"""

# Funções utilitárias
def display_welcome_message():
    welcome_text = """
🐦‍🔥 Bem-vindo ao MindForge, o seu assistente interativo para criação de mundos! 🐉\n\n

**O que eu posso fazer?**\n\n

Vou te ajudar a criar e desenvolver qualquer aspecto do seu mundo. 🗺️ Juntos podemos criar continentes, raças, personagens, criaturas, artefatos, tecnologias e muito mais! O limite é a sua imaginação!\n

Ao interagir comigo, você pode criar ou editar um arquivo existente em seu Google Drive.\n

Vamos começar?
    """
    display(Markdown(welcome_text))

def show_main_interface():
    user_input = widgets.Textarea(
        placeholder="Descreva sua ideia ou clique em Gerar para uma sugestão surpresa!",
        style={'description_width': 'initial'},
        layout=widgets.Layout(width='55%', min_width='320px')
    )
    gerar_btn = widgets.Button(
        description="Gerar",
        button_style='primary',
        layout=widgets.Layout(width='150px', min_width='100px')
    )
    acessar_btn = widgets.Button(
        description="Acessar compêndio",
        button_style='info',
        layout=widgets.Layout(width='170px', min_width='120px')
    )
    output = widgets.Output()
    btns_box = widgets.HBox([gerar_btn, acessar_btn])

    def on_gerar(_):
        with output:
            clear_output()
            req = user_input.value
            display(Markdown("Gerando..."))
            ai_text = generate_creative_content(req, current_world_context)
            display(Markdown(ai_text))
            confirmar_btn = widgets.Button(
                description="Confirmar e Salvar",
                button_style='success',
                layout=widgets.Layout(width='180px', min_width='120px')
            )
            gerar_novamente_btn = widgets.Button(
                description="Gerar Outra Ideia",
                button_style='warning',
                layout=widgets.Layout(width='170px', min_width='120px')
            )
            btns_confirm = widgets.HBox([confirmar_btn, gerar_novamente_btn])

            def on_confirm(_):
                ok = update_google_doc(document_id, ai_text)
                with output:
                    clear_output()
                    if ok:
                        link_html = f"""
                        <div style='font-size: 1em; margin: 20px 0;'>
                          O seu compêndio foi atualizado! <b><a href="{document_link}" target="_blank">Clique aqui para acessá-lo!</a></b>
                        </div>
                        """
                        display(widgets.HTML(link_html))
                    else:
                        display(Markdown("Erro ao salvar."))

            def on_gerar_novo(_):
                with output:
                    clear_output()
                on_gerar(None)
            confirmar_btn.on_click(on_confirm)
            gerar_novamente_btn.on_click(on_gerar_novo)
            display(btns_confirm)

    def on_acessar(_):
        display(Javascript(f'window.open("{document_link}", "_blank");'))

    gerar_btn.on_click(on_gerar)
    acessar_btn.on_click(on_acessar)

    return widgets.VBox([
        widgets.HTML("<h3>O que você tem em mente? Conta aí 😉</h3>"),
        user_input, btns_box, output
    ])

def find_or_create_document(name_hint=None):
    global document_id, document_title, document_link, current_world_context

    output = widgets.Output()
    box = widgets.Output()
    doc_select_output = widgets.Output()
    confirm_btn = widgets.Button(description="Confirmar seleção", button_style='success')
    confirm_btn.layout.display = 'none'

    selected_file = {'file': None}

    def after_selection():
        box.clear_output()
        with box:
            display(widgets.VBox([
            widgets.HTML(f"<h3>Compêndio selecionado: <b>{document_title}</b></h3>"),
            show_main_interface()
        ]))
    def on_create(_):
        doc_name = name_text.value.strip() or "Meu Compêndio de Mundos Criativos"
        file_metadata = {'name': doc_name, 'mimeType': 'application/vnd.google-apps.document'}
        try:
            file = drive_service.files().create(body=file_metadata, fields='id, webViewLink, name').execute()
            global document_id, document_title, document_link, current_world_context
            document_id = file.get('id')
            document_link = file.get('webViewLink')
            document_title = file.get('name')
            current_world_context = f"# {document_title}\n\n*Este compêndio foi iniciado com o Assistente Interativo de Criação de Mundos.*\n\n"
            update_google_doc(document_id, current_world_context, is_initial_creation=True)
            after_selection()
        except Exception as e:
            with output:
                clear_output()
                print("Erro ao criar documento:", e)

    def on_search(_):
        with doc_select_output:
            clear_output()
            display(widgets.HTML('<span style="font-weight:bold;color:#376;">Procurando...</span>'))
        query = f"name contains '{search_text.value}' and mimeType='application/vnd.google-apps.document' and trashed=false"
        try:
            results = drive_service.files().list(q=query, spaces='drive', pageSize=10, fields='files(id, name, webViewLink)').execute()
            items = results.get('files', [])
            if items:
                options = [(item.get('name'), item) for item in items]
                doc_select.options = options
                with doc_select_output:
                    clear_output()
                    display(widgets.HTML(f"<span style='font-weight:bold;'>Documentos encontrados:</span>"))
                    display(doc_select)
                    confirm_btn.layout.display = ''
            else:
                doc_select.options = []
                with doc_select_output:
                    clear_output()
                    display(widgets.HTML("<i>Nenhum documento encontrado.</i>"))
                    confirm_btn.layout.display = 'none'
        except Exception as e:
            with doc_select_output:
                clear_output()
                print("Erro ao buscar documentos:", e)

    def on_select_doc(change):
        selected = change['new']
        selected_file['file'] = selected
        confirm_btn.layout.display = '' if selected else 'none'

    def on_confirm_selection(_):
        selected = selected_file['file']
        if selected:
            global document_id, document_title, document_link, current_world_context
            document_id = selected['id']
            document_title = selected['name']
            document_link = selected['webViewLink']
            current_world_context = read_google_doc_content(document_id)
            after_selection()

    text_layout = widgets.Layout(width='320px', min_width='200px')
    btn_layout = widgets.Layout(width='180px', min_width='120px')
    dropdown_layout = widgets.Layout(width='320px', min_width='200px')

    name_text = widgets.Text(
        description="Crie um novo compêndio:",
        placeholder="Ex: Crônicas Fantásticas",
        style={'description_width': 'initial'},
        layout=text_layout
    )
    create_btn = widgets.Button(
        description="Criar novo compêndio",
        button_style='success',
        layout=btn_layout
    )
    create_btn.on_click(on_create)

    search_text = widgets.Text(
        description="Buscar compêndio:",
        placeholder="Nome ou parte do nome",
        style={'description_width': 'initial'},
        layout=text_layout
    )
    search_btn = widgets.Button(
        description="Buscar",
        button_style='info',
        layout=btn_layout
    )
    search_btn.on_click(on_search)

    doc_select = widgets.Dropdown(options=[], description="Selecionar:", layout=dropdown_layout, style={'description_width': 'initial'})
    doc_select.observe(on_select_doc, names='value')

    confirm_btn.on_click(on_confirm_selection)

    with box:
        display(widgets.VBox([
            widgets.HTML("<div style='font-size:1.1em; margin-bottom: 15px;'><b>Crie um novo compêndio ou pesquise por um já existente no seu Google Drive:</b></div>"),
            widgets.HBox([name_text, create_btn]),
            widgets.HBox([search_text, search_btn]),
            doc_select_output,
            confirm_btn,
            output
        ]))

    display(box)


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
        print("Erro ao ler conteúdo do documento:", e)
        return ""

import re

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
        print("Erro ao atualizar documento:", e)
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
        print("Erro IA:", e)
        return "Erro IA."

def present_suggestion_and_get_feedback(suggestion_markdown, drive_service, docs_service):
    global document_id, document_link

    if not suggestion_markdown or suggestion_markdown.strip().startswith("Desculpe"):
        display(Markdown(f"⚠️ {suggestion_markdown}"))
        return "regenerate"

    print("\n✨ Minha Sugestão para Você ✨\n" + "="*40)
    display(Markdown(suggestion_markdown))
    print("="*40)

    while True:
        print("\nO que você gostaria de fazer?")
        print("1. Confirmar (e adicionar ao seu compêndio)")
        print("2. Gerar novamente (tentar uma nova ideia para o mesmo pedido)")
        print("3. Sair do assistente")
        user_choice = input("Digite sua escolha (1, 2 ou 3): ")

        if user_choice == '1':
            print("\n✅ Confirmado! Adicionando ao seu compêndio...")
            success = update_google_doc(docs_service, document_id, suggestion_markdown)
            if success:
                display(Markdown(f"Perfeito! Seu compêndio foi atualizado com a sua mais nova criação. Se quiser acessá-lo diretamente, [clique aqui]({document_link})."))
            else:
                display(Markdown("Houve um erro ao salvar no Google Doc. A criação não foi adicionada."))
            return "confirmed"
        elif user_choice == '2':
            print("\nEntendido! 🧐 Vou tentar gerar uma nova sugestão para o seu pedido anterior...")
            return "regenerate"
        elif user_choice == '3':
            print("\nAté logo! Espero ter ajudado na sua jornada criativa! 👋")
            return "exit"
        else:
            print("Opção inválida. Por favor, escolha 1, 2 ou 3.")

def world_builder_chatbot():
    global current_world_context, document_id, document_link
    display_welcome_message()
    find_or_create_document()

"""#Rode o assistente! 🎲"""

# Executar Assistente Interativo para Criação de Mundos!
world_builder_chatbot()