import os
import requests
from bs4 import BeautifulSoup
from datetime import datetime
import dash
from dash import html, dcc, Input, Output, State, callback_context
import dash_bootstrap_components as dbc
import openai
from google.cloud import texttospeech

summarization_dir = os.path.join(os.getcwd(), 'Summarization')
assets_dir = os.path.join(summarization_dir, 'assets')
if not os.path.exists(assets_dir):
    os.makedirs(assets_dir)

# Google Cloud 서비스 계정 키 파일 설정
os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = "C:\\Python\\metadata\\credential.json"

# OpenAI API 키 설정
openai.api_key = os.getenv('OPENAI_API_KEY')

# Google Fonts 추가
external_stylesheets = [
    'https://fonts.googleapis.com/css2?family=Gowun+Dodum&family=Black+Han+Sans&display=swap',
]

app = dash.Dash(__name__, external_stylesheets=external_stylesheets)

# 호버링 효과 추가 (CSS에서 처리할 것)
hover_effect = {
    'className': 'hover-effect'
}

spinner_effect = {
    'className': 'spinner'
}

# 분야별 요약 프롬프트 설정
summary_prompts = {
    '정치': '정치인의 인용을 위주로 요약하세요.',
    '경제': '화폐 단위와 수치, 과거 기간 또는 다른 나라와의 비교를 강조하여 요약하세요.',
    '사건/사고': '언제, 어디서, 어떻게 일어난 사건인지 육하원칙을 중심으로 명확히 요약하세요.',
}

# 공통 스타일
common_style = {
    'width': '100%',
    'marginBottom': '20px',
    'marginTop': '10px',
    'fontFamily': 'Gowun Dodum',
    'fontSize': '16px',
    'lineHeight': '1.5',
    'border': '2px solid black',
    'cursor': 'pointer',
    'transition': 'background-color 0.3s, color 0.3s',
    'boxShadow': '0 4px 8px rgba(0, 0, 0, 0.1)',
    'borderRadius': '8px',
    'padding': '4px',
    'textShadow': '1px 1px 2px rgba(0, 0, 0, 0.5)',
}

# 버튼 전용 스타일
button_style_half = {
    'width': '50%',
    'marginBottom': '20px',
    'marginTop': '10px',
    'fontFamily': 'Gowun Dodum',
    'fontSize': '16px',
    'lineHeight': '1.5',
    'border': '2px solid black',
    'cursor': 'pointer',
    'transition': 'background-color 0.3s, color 0.3s',
    'boxShadow': '0 4px 8px rgba(0, 0, 0, 0.1)',
    'padding': '4px',
    'borderRadius': '8px',
}

app.layout = html.Div([
    html.Div([
        html.Img(src="/assets/LOGO_딩딩핑거.jpg", height="20px", style={'marginRight': '10px'}),
        html.H1("딩딩 기사요약기", style={'fontSize': '30px', 'fontFamily': 'Black Han Sans', 'marginRight': '10px', 'marginBottom': '10px'})
    ], style={'display': 'flex', 'alignItems': 'center', 'padding': '10px', 'backgroundColor': '#f0f0f0', 'borderBottom': '1px solid #ddd', 'flex': '1', 'marginBottom': '20px'}),

    dcc.Store(id='history-store'),

    html.Div([
        html.Div([
            html.H3("요약 히스토리", style=common_style),
            dcc.Textarea(id='history-output', value='여기에 기사 요약 히스토리가 표시됩니다.', style={**common_style, 'height': '300px'}),
            dcc.Textarea(id='anchor-intro', placeholder='앵커멘트를 입력하세요', style={**common_style, 'height': '60px'}),
            dcc.Textarea(id='anchor-closing', placeholder='클로징 멘트를 입력하세요', style={**common_style, 'height': '60px'}),
            html.Button('모든 큐시트 음성 생성', id='generate-all-audio-button', className='hover-effect', style={**common_style, **hover_effect}),
            html.Button("Export to File", id="export-button", n_clicks=0, className='hover-effect', style={**common_style, **hover_effect}),
            html.Div(id='export-status')
        ], className='column', style={'flex': '1'}),
        
        html.Div(id='loading-output'),
        html.Div([
            dcc.Dropdown(
                id='article-category-select',
                options=[{'label': i, 'value': i} for i in ['정치', '경제', '사건/사고']],
                value='정치',
                style={'marginBottom': '10px'}
            ),
            dcc.Input(id='url-input', type='text', placeholder='기사 URL을 입력하세요:', style=common_style),
            dcc.Loading(id="fetch-article-loading", type="default", children=[
                html.Button('본문 불러오기', id='fetch-article-button', n_clicks=0, className='hover-effect', style={**common_style, **hover_effect})
            ]),
            dcc.Textarea(id='article-output', style={**common_style, 'height': '450px'}),
        ], className='column', style={'flex': '3'}),

        html.Div([
            dcc.Loading(id="summarize-loading", type="default", children=[
                html.Button('요약하기', id='summarize-button', n_clicks=0, className='hover-effect', style={**common_style, **hover_effect})
            ]),
        ], className='column', style={'flex': '0.5', 'display': 'flex', 'alignItems': 'center', 'justifyContent': 'center'}),

        html.Div([
            dcc.Textarea(id='summary-output', readOnly=True, style={**common_style, 'height': '180px'}),
            dcc.Textarea(id='editable-summary-output', style={**common_style, 'height': '180px'}),
            html.Div([
                html.Button('음성 듣기', id='listen-button', className='hover-effect', style={**button_style_half, **hover_effect}),
                html.Button('음성 저장', id='download-button', className='hover-effect', style={**button_style_half, **hover_effect}),
            ], style={'display': 'flex'}),
            html.Audio(id='audio-player', controls=True, style={'width': '100%', 'marginBottom': '10px'}),
            html.A(id='download-link', children='다운로드', href="", style={'display': 'none', 'marginBottom': '10px'}),
            html.Button('저장하기', id='save-summary-button', className='hover-effect', style={**common_style, **hover_effect}),
        ], className='column', style={'flex': '4'})
    ], style={'display': 'flex', 'width': '90%', 'marginLeft': 'auto', 'marginRight': 'auto', 'gap': '20px'})
])

@app.callback(
    Output('article-output', 'value'),
    [Input('fetch-article-button', 'n_clicks')],
    [State('url-input', 'value')],
    prevent_initial_call=True
)
def fetch_article(n_clicks, url):
    if n_clicks and url:
        spinner = html.Div(className='spinner', style={'display': 'flex', 'justifyContent': 'center'})
        response = requests.get(url)
        soup = BeautifulSoup(response.content, 'html.parser')
        article_text = soup.find('div', {'class': 'newsct_article _article_body'}).get_text()
        return article_text
    return "기사를 불러오려면 URL을 입력하고 버튼을 클릭하세요."

@app.callback(
    [Output('summary-output', 'value'), Output('editable-summary-output', 'value'), Output('loading-output', 'children')],
    [Input('summarize-button', 'n_clicks')],
    [State('article-output', 'value')],
    prevent_initial_call=True
)
def summarize_article(n_clicks, article_text):
    if n_clicks and article_text:
        spinner = html.Div(className='spinner', style={'display': 'flex', 'justifyContent': 'center'})
        try:
            response = openai.ChatCompletion.create(
                model="gpt-4",
                messages=[
                    {"role": "system", "content": f"당신은 긴 기사를 {summary_prompts} 방송용 짧은 기사 3줄로 요약해주는 도우미입니다. 우선 전체 요약된 내용을 한 줄 30글자 내로 제목으로 뽑아서 출력된 단신 맨 위에 표시해. 문장의 끝은 '했습니다' 또는 '입니다' 등 공손한 말투로 마무리해. 그리고 한 문장이 끝나면 한 줄을 띄우고 다음 문장을 출력해."},
                    {"role": "user", "content": article_text}
                ]
            )
            summary = response.choices[0].message["content"]
            # 제목과 내용을 분리
            title, body = summary.split('\n', 1)
            return summary, body.strip(), None
        except Exception as e:
            print(f"요약 과정에서 오류 발생: {e}")
            return "요약을 진행할 수 없습니다.", "요약을 진행할 수 없습니다.", None
    return dash.no_update, dash.no_update, html.Div(spinner)

@app.callback(
    [Output('history-output', 'value'), Output('history-store', 'data'), Output('export-status', 'children')],
    [Input('save-summary-button', 'n_clicks'), Input('export-button', 'n_clicks')],
    [State('summary-output', 'value'), State('editable-summary-output', 'value'), State('history-store', 'data'), State('anchor-intro', 'value'), State('anchor-closing', 'value')]
)
def manage_history(save_clicks, export_clicks, summary_title, summary_full, history, anchor_intro, anchor_closing):
    ctx = callback_context
    button_id = ctx.triggered[0]['prop_id'].split('.')[0]

    if button_id == 'save-summary-button' and save_clicks:
        new_history = history if history else []
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M")
        new_history.append({'timestamp': timestamp, 'title': summary_title[:30], 'full_summary': summary_full})
        history_text = "\n".join([f"{item['timestamp']} - {item['title']}" for item in new_history])
        return history_text, new_history, dash.no_update

    elif button_id == 'export-button' and export_clicks:
        if history:
            file_path = 'C:/Python/Summarization/history_data.txt'
            with open(file_path, 'w', encoding='utf-8') as file:
                file.write(f"{anchor_intro}\n\n")
                for item in history:
                    file.write(f"Timestamp: {item['timestamp']}\nTitle: {item['title']}\nSummary: {item['full_summary']}\n\n")
                file.write(f"{anchor_closing}\n")
            return dash.no_update, dash.no_update, f"History exported to {file_path}."
        else:
            return dash.no_update, dash.no_update, "No history to export."

    return dash.no_update, dash.no_update, dash.no_update

@app.callback(
    [Output('audio-player', 'src'), Output('download-link', 'href'), Output('download-link', 'children')],
    [Input('listen-button', 'n_clicks'), Input('generate-all-audio-button', 'n_clicks')],
    [State('editable-summary-output', 'value'), State('history-store', 'data'), State('anchor-intro', 'value'), State('anchor-closing', 'value')]
)
def generate_speech(n_clicks_listen, n_clicks_all, summary_text, history, anchor_intro, anchor_closing):
    ctx = callback_context
    button_id = ctx.triggered[0]['prop_id'].split('.')[0]

    client = texttospeech.TextToSpeechClient()

    if button_id == 'listen-button' and n_clicks_listen:
        combined_text = f"{anchor_intro}\n\n{summary_text}\n\n{anchor_closing}"
        input_text = texttospeech.SynthesisInput(text=combined_text)
    elif button_id == 'generate-all-audio-button' and n_clicks_all:
        history = history if history else []

        ssml_text = "<speak>" + anchor_intro
        for item in history:		
            ssml_text += f"\n\n{item['full_summary']}\n\n<break time='2000ms'/>"
        ssml_text += f"{anchor_closing}</speak>"
        
        input_text = texttospeech.SynthesisInput(ssml=ssml_text)
          
        
    else:
        return dash.no_update, dash.no_update, dash.no_update

    voice = texttospeech.VoiceSelectionParams(language_code="ko-KR", ssml_gender=texttospeech.SsmlVoiceGender.NEUTRAL)
    audio_config = texttospeech.AudioConfig(audio_encoding=texttospeech.AudioEncoding.MP3)
    response = client.synthesize_speech(input=input_text, voice=voice, audio_config=audio_config)
    audio_content = response.audio_content

    if button_id == 'listen-button' and n_clicks_listen:
        filename = f"audio_{datetime.now().strftime('%Y%m%d%H%M%S')}.mp3"
    elif button_id == 'generate-all-audio-button' and n_clicks_all:
        filename = f"all_audio_{datetime.now().strftime('%Y%m%d%H%M%S')}.mp3"
    filepath = os.path.join(assets_dir, filename)

    with open(filepath, 'wb') as f:
        f.write(audio_content)

    audio_url = f"/assets/{filename}"
    download_url = f"/assets/{filename}"
    return audio_url, download_url, "Download Audio"

if __name__ == '__main__':
    app.run_server(debug=True)

