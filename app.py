from flask import Flask, render_template, request
import re

app = Flask(__name__)

@app.route("/", methods=["GET", "POST"])
def index():
    output = []
    first_follow = {'first': 'N/A', 'follow': 'N/A', 'valid': False}
    grammar_input = ""
    entrada = ""
    tabla_predictiva = []
    
    if request.method == "POST":
        grammar_input = request.form.get("grammar", "")
        entrada = request.form.get("entrada", "")
        output, first_follow, tabla_predictiva = run_parser(grammar_input, entrada)
    
    return render_template(
        "index.html",
        output=output,
        first_follow=first_follow,
        grammar=grammar_input,
        entrada=entrada,
        tabla_predictiva=tabla_predictiva
    )

def run_parser(grammar_text, cadena_input):
    output = []
    lines = grammar_text.strip().split('\n')
    sent = [line.strip() for line in lines if line.strip() != ""]

    if not sent or not cadena_input:
        return [], {'first': 'N/A', 'follow': 'N/A', 'valid': False}, []

    variables = []
    terminales = []
    start = [sent[0][0]]  # primer símbolo no terminal

    # Limpieza
    for i in range(len(sent)):
        sent[i] = sent[i].replace(" ", "").replace("→", "->")

    grammar = {}
    tabla = {}
    reglas = {}

    for line in sent:
        if "->" not in line:
            continue
        izquierda, derecha = line.split("->", 1)
        izquierda = izquierda.strip()
        derecha = derecha.strip()

        if izquierda not in grammar:
            grammar[izquierda] = {"tipo": "V", "first": [], "follow": []}

        if izquierda not in tabla:
            tabla[izquierda] = {}

        if derecha == "":
            produccion = ['ε']
        else:
            produccion = list(derecha)

        reglas[f"{izquierda}->{''.join(produccion)}"] = {"Izq": izquierda, "Der": produccion}

        for simbolo in produccion:
            if simbolo.islower() and simbolo not in terminales and simbolo != 'ε':
                terminales.append(simbolo)
            elif simbolo.isupper() and simbolo not in grammar:
                grammar[simbolo] = {"tipo": "V", "first": [], "follow": []}

    for t in terminales:
        grammar[t] = {"tipo": "T", "first": [t]}

    grammar[start[0]]["follow"].append("$")

    # Calcular FIRST
    changed = True
    while changed:
        changed = False
        for r in reglas.values():
            A = r["Izq"]
            alpha = r["Der"]
            before = set(grammar[A]["first"])
            if alpha[0] == 'ε':
                grammar[A]["first"].append('ε')
            else:
                for symbol in alpha:
                    grammar[A]["first"] += [f for f in grammar[symbol]["first"] if f != 'ε']
                    if 'ε' not in grammar[symbol]["first"]:
                        break
                else:
                    grammar[A]["first"].append('ε')
            grammar[A]["first"] = list(set(grammar[A]["first"]))
            if set(grammar[A]["first"]) != before:
                changed = True

    # Calcular FOLLOW
    changed = True
    while changed:
        changed = False
        for r in reglas.values():
            A = r["Izq"]
            alpha = r["Der"]
            for i in range(len(alpha)):
                B = alpha[i]
                if B in grammar and grammar[B]["tipo"] == "V":
                    follow_before = set(grammar[B]["follow"])
                    if i + 1 < len(alpha):
                        beta = alpha[i + 1:]
                        first_beta = []
                        for symbol in beta:
                            first_beta += [f for f in grammar[symbol]["first"] if f != 'ε']
                            if 'ε' not in grammar[symbol]["first"]:
                                break
                        else:
                            first_beta += grammar[A]["follow"]
                        grammar[B]["follow"] += first_beta
                    else:
                        grammar[B]["follow"] += grammar[A]["follow"]
                    grammar[B]["follow"] = list(set(grammar[B]["follow"]))
                    if set(grammar[B]["follow"]) != follow_before:
                        changed = True

    # Llenar tabla predictiva
    for r in reglas.values():
        A = r["Izq"]
        alpha = r["Der"]
        first_alpha = []
        if alpha[0] == 'ε':
            first_alpha = grammar[A]["follow"]
        else:
            for symbol in alpha:
                first_alpha += [f for f in grammar[symbol]["first"] if f != 'ε']
                if 'ε' not in grammar[symbol]["first"]:
                    break
            else:
                first_alpha += grammar[A]["follow"]

        for terminal in first_alpha:
            if terminal not in tabla[A]:
                tabla[A][terminal] = r

    # Agregar acciones EXT y EXP
    for v in grammar:
        if grammar[v]["tipo"] == "V":
            for t in terminales + ['$']:
                if t not in tabla[v]:
                    if t in grammar[v]["follow"] or t == '$':
                        tabla[v][t] = {"Izq": v, "Der": ["EXT"]}
                    else:
                        tabla[v][t] = {"Izq": v, "Der": ["EXP"]}

    # Preparar tabla predictiva para mostrar
    terminales_unicos = list(set(terminales + ['$']))
    variables_unicas = [v for v in grammar.keys() if grammar[v]["tipo"] == "V"]
    
    tabla_predictiva = []
    for v in variables_unicas:
        fila = {"variable": v, "producciones": {}}
        for t in terminales_unicos:
            if t in tabla[v]:
                produccion = tabla[v][t]
                if produccion["Der"][0] == "EXT":
                    fila["producciones"][t] = "EXT"
                elif produccion["Der"][0] == "EXP":
                    fila["producciones"][t] = "EXP"
                else:
                    fila["producciones"][t] = f"{produccion['Izq']} → {''.join(produccion['Der'])}"
            else:
                fila["producciones"][t] = ""
        tabla_predictiva.append(fila)

    # PARSER
    cadena = cadena_input + "$"
    pila = [start[0]]
    index = 0
    valid = False

    output.append({"pila": ' '.join(pila[::-1]), "entrada": cadena[index:], "accion": "Inicio del análisis"})

    while True:
        if not pila:
            if cadena[index] == "$":
                output.append({"pila": "", "entrada": "$", "accion": "CADENA VÁLIDA ✅"})
                valid = True
            else:
                output.append({"pila": "", "entrada": cadena[index:], "accion": "Cadena no válida ❌ (entrada restante)"})
            break

        top = pila[-1]
        actual = cadena[index]

        if top == actual:
            output.append({"pila": ' '.join(pila[::-1]), "entrada": cadena[index:], "accion": f"Match: {actual}"})
            pila.pop()
            index += 1
        elif top in grammar and grammar[top]["tipo"] == "T":
            output.append({"pila": ' '.join(pila[::-1]), "entrada": cadena[index:], "accion": "Error: token inesperado"})
            break
        elif top in tabla and actual in tabla[top]:
            produccion = tabla[top][actual]
            if produccion["Der"][0] == "EXT":
                output.append({"pila": ' '.join(pila[::-1]), "entrada": cadena[index:], "accion": f"Extraer: {top} (EXT)"})
                pila.pop()
            elif produccion["Der"][0] == "EXP":
                output.append({"pila": ' '.join(pila[::-1]), "entrada": cadena[index:], "accion": f"Explorar: {actual} (EXP)"})
                index += 1
                if index >= len(cadena):
                    output.append({"pila": ' '.join(pila[::-1]), "entrada": "", "accion": "Cadena no válida ❌ (fin de entrada)"})
                    break
            else:
                output.append({"pila": ' '.join(pila[::-1]), "entrada": cadena[index:], "accion": f"Regla: {produccion['Izq']} → {' '.join(produccion['Der'])}"})
                pila.pop()
                if produccion["Der"][0] != 'ε':
                    for sym in reversed(produccion["Der"]):
                        pila.append(sym)
        else:
            first = grammar[top]["first"]
            follow = grammar[top]["follow"]
            if actual == "$" or actual in follow:
                output.append({"pila": ' '.join(pila[::-1]), "entrada": cadena[index:], "accion": f"Extraer: {top}"})
                pila.pop()
            else:
                output.append({"pila": ' '.join(pila[::-1]), "entrada": cadena[index:], "accion": f"Explorar: {actual}"})
                index += 1
                if index >= len(cadena):
                    output.append({"pila": ' '.join(pila[::-1]), "entrada": "", "accion": "Cadena no válida ❌ (fin de entrada)"})
                    break

    # Preparar First y Follow para mostrar
    first_output = []
    follow_output = []
    for var in sorted(grammar.keys()):
        if grammar[var]["tipo"] == "V":
            first_output.append(f"{var}: {', '.join(sorted(grammar[var]['first']))}")
            follow_output.append(f"{var}: {', '.join(sorted(grammar[var]['follow']))}")

    return output, {
        'first': '\n'.join(first_output),
        'follow': '\n'.join(follow_output),
        'valid': valid
    }, tabla_predictiva

if __name__ == "__main__":
    app.run(debug=True)
