from flask import Flask, render_template, request, redirect, url_for, flash, jsonify
import json
from werkzeug.utils import secure_filename
from os.path import exists
import os

app = Flask(__name__)
app.secret_key = os.urandom(24) # Chave secreta para sessões

if not exists('cardapio.json'):
    with open('cardapio.json', 'w') as f:
        json.dump([], f)

def carregar_cardapio():
    with open('cardapio.json', 'r', encoding='utf-8') as f:
        cardapio = json.load(f)
    
    # Adicionar ordem padrão para itens sem o campo
    for item in cardapio:
        if 'ordem' not in item:
            item['ordem'] = 0  # Valor padrão para itens sem ordem
    
    return cardapio

def salvar_cardapio(cardapio):
    with open('cardapio.json', 'w', encoding='utf-8') as f:
        json.dump(cardapio, f, indent=4, ensure_ascii=False)

UPLOAD_FOLDER = 'static/imagens'
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif'}

app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

def allowed_file(filename):
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

@app.route('/')
def exibir_cardapio():
    cardapio = carregar_cardapio()
    cardapio_visivel = [item for item in cardapio if item.get('visivel', True)]

    # Ordenar os itens por ordem
    cardapio_visivel.sort(key=lambda x: x.get('ordem', 0))

    # Agrupar itens por categoria
    cardapio_por_categoria = {}
    for item in cardapio_visivel:
        categoria = item.get('categoria')
        if categoria:
            if categoria not in cardapio_por_categoria:
                cardapio_por_categoria[categoria] = []
            cardapio_por_categoria[categoria].append(item)

    # Ordenar as categorias na ordem desejada (opcional)
    ordem_categorias = ["ENTRADAS", "SALADAS", "PRATO KIDS", "SANDUÍCHES E BURGUES", "PARRILLA", "TUCUNDUVA SMOKED", "ACOMPANHAMENTOS", "SOBREMESAS", "BEBIDAS", "CERVEJAS", "DRINKS","CAFÉ", "VINHO TINTO", "VINHO BRANCO", "VINHO ROSÉ"]
    cardapio_ordenado_por_categoria = {categoria: cardapio_por_categoria.get(categoria, []) for categoria in ordem_categorias if categoria in cardapio_por_categoria}
    cardapio_ordenado_por_categoria.update({cat: itens for cat, itens in cardapio_por_categoria.items() if cat not in ordem_categorias})

    return render_template('cardapio.html', cardapio_por_categoria=cardapio_ordenado_por_categoria)

# Rota para a página inicial do admin
@app.route('/admin')
def admin_home():
    return render_template('admin_home.html')

# Rota para o formulário de adicionar item
@app.route('/admin/adicionar_form') 
def adicionar_form():
    return render_template('adicionar_item.html')



# Rota para adicionar item
@app.route('/admin/adicionar', methods=['POST'])
def adicionar_item():
    nome = request.form['nome']
    descricao = request.form['descricao']
    preco = request.form['preco']
    categoria = request.form['categoria']
    cardapio = carregar_cardapio()
    categoria_itens = [item for item in cardapio if item.get('categoria') == categoria]
    ordem = len(categoria_itens) + 1
    imagem = None # Inicializa o campo imagem

    if not nome or not preco or not categoria:
        flash('Nome, preço e categoria são obrigatórios.', 'error')
        return redirect(url_for('adicionar_form'))

    try:
        preco = float(preco)
    except ValueError:
        flash('Preço inválido.', 'error')
        return redirect(url_for('adicionar_form'))

    # Lidar com o upload da imagem
    if 'imagem' in request.files:
        file = request.files['imagem']
        if file and allowed_file(file.filename):
            filename = secure_filename(file.filename)
            file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
            imagem = filename

    novo_id = len(cardapio) + 1
    novo_item = {
        'id': novo_id,
        'nome': nome,
        'descricao': descricao,
        'preco': preco,
        'visivel': True,
        'categoria': categoria,
        'ordem': ordem,
        'imagem': imagem # Novo campo
    }
    cardapio.append(novo_item)
    salvar_cardapio(cardapio)
    flash(f'Item "{nome}" adicionado com sucesso!', 'success')
    return redirect(url_for('gerenciar_itens'))

# Rota para editar item (formulário)
@app.route('/admin/editar/<int:item_id>')
def editar_form(item_id):
    cardapio = carregar_cardapio()
    item_para_editar = next((item for item in cardapio if item['id'] == item_id), None)
    if item_para_editar:
        return render_template('editar_item.html', item=item_para_editar)
    else:
        flash('Item não encontrado.', 'warning')
        return redirect(url_for('gerenciar_itens'))

# Rota para editar item
@app.route('/admin/editar/<int:item_id>', methods=['POST'])
def editar_item(item_id):
    # Obter os dados do formulário
    nome = request.form.get('nome')
    descricao = request.form.get('descricao')
    preco = request.form.get('preco')
    categoria = request.form.get('categoria')
    imagem_atual = request.form.get('imagem_atual')
    nova_imagem = None

    # Validação dos campos obrigatórios
    if not nome or not preco or not categoria:
        flash('Nome, preço e categoria são obrigatórios.', 'error')
        return redirect(url_for('editar_form', item_id=item_id))

    # Validar o preço
    try:
        preco = float(preco)
    except ValueError:
        flash('Preço inválido. Insira um valor numérico.', 'error')
        return redirect(url_for('editar_form', item_id=item_id))

    # Lidar com o upload de uma nova imagem
    if 'nova_imagem' in request.files:
        file = request.files['nova_imagem']
        if file and allowed_file(file.filename):
            filename = secure_filename(file.filename)
            file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
            nova_imagem = filename

    # Carregar o cardápio e atualizar o item
    cardapio = carregar_cardapio()
    item = next((i for i in cardapio if i['id'] == item_id), None)

    if item:
        # Atualizar os dados do item
        item['nome'] = nome
        item['descricao'] = descricao
        item['preco'] = preco
        item['categoria'] = categoria
        item['imagem'] = nova_imagem if nova_imagem else imagem_atual

        # Salvar as alterações no cardápio
        salvar_cardapio(cardapio)
        flash(f'Item "{nome}" editado com sucesso!', 'success')
    else:
        flash('Item não encontrado.', 'warning')

    # Redirecionar para a página de gerenciamento
    return redirect(url_for('gerenciar_itens'))

# Rota para gerenciar itens
@app.route('/admin/gerenciar')
def gerenciar_itens():
    cardapio = carregar_cardapio()

    # Ordenar os itens por ordem
    cardapio.sort(key=lambda x: x.get('ordem', 0))

    # Agrupar itens por categoria para gerenciamento
    cardapio_por_categoria = {}
    for item in cardapio:
        categoria = item.get('categoria')
        if categoria:
            if categoria not in cardapio_por_categoria:
                cardapio_por_categoria[categoria] = []
            cardapio_por_categoria[categoria].append(item)

    # Ordenar as categorias na ordem desejada (opcional)
    ordem_categorias = ["ENTRADAS", "SALADAS", "PRATO KIDS", "SANDUÍCHES E BURGUES", "PARRILLA", "TUCUNDUVA SMOKED", "ACOMPANHAMENTOS", "SOBREMESAS", "BEBIDAS", "CERVEJAS", "DRINKS","CAFÉ", "VINHO TINTO", "VINHO BRANCO", "VINHO ROSÉ"]
    cardapio_ordenado_por_categoria = {categoria: cardapio_por_categoria.get(categoria, []) for categoria in ordem_categorias if categoria in cardapio_por_categoria}
    cardapio_ordenado_por_categoria.update({cat: itens for cat, itens in cardapio_por_categoria.items() if cat not in ordem_categorias})

    return render_template('gerenciar_itens.html', cardapio_por_categoria=cardapio_ordenado_por_categoria)

# Rota para alterar a visibilidade do item
@app.route('/admin/visibilidade/<int:item_id>', methods=['POST'])
def alterar_visibilidade(item_id):
    cardapio = carregar_cardapio()
    item_encontrado = False
    for item in cardapio:
        if item['id'] == item_id:
            item['visivel'] = not item.get('visivel', True)
            item_encontrado = True
            flash(f"Visibilidade do item '{item['nome']}' alterada com sucesso!", 'success')
            break
    if item_encontrado:
        salvar_cardapio(cardapio)
    else:
        flash(f"Item com ID {item_id} não encontrado.", 'warning')
    return redirect(url_for('gerenciar_itens'))

# Rota para remover item do cardápio
@app.route('/admin/remover/<int:item_id>', methods=['POST', 'DELETE'])
def remover_item(item_id):
    cardapio = carregar_cardapio()
    item_removido = False
    for i, item in enumerate(cardapio):
        if item['id'] == item_id:
            del cardapio[i]
            item_removido = True
            flash(f'Item "{item["nome"]}" removido com sucesso!', 'success')
            break
    if item_removido:
        salvar_cardapio(cardapio)
    else:
        flash(f'Item com ID {item_id} não encontrado.', 'warning')
    return redirect(url_for('gerenciar_itens'))

# Rota para editar a ordem dos itens
@app.route('/admin/ordenar_itens', methods=['POST'])
def ordenar_itens():
    data = request.get_json()
    categoria = data.get('categoria')
    nova_ordem_ids = data.get('ordem')

    if not categoria or not nova_ordem_ids:
        return jsonify({'success': False, 'error': 'Dados inválidos recebidos.'})

    cardapio = carregar_cardapio()
    itens_na_categoria = [item for item in cardapio if item.get('categoria') == categoria]
    itens_por_id = {item['id']: item for item in itens_na_categoria}

    # Atualizar a ordem dos itens na categoria
    for i, item_id in enumerate(nova_ordem_ids):
        item = itens_por_id.get(int(item_id))
        if item:
            item['ordem'] = i + 1

    # Salvar o cardápio atualizado no JSON
    salvar_cardapio(cardapio)
    return jsonify({'success': True})

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
    # Ou use o seu endereço IP local:
    # app.run(host='192.168.15.47', port=5000, debug=True)go