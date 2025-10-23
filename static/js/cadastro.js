// Arquivo: static/js/cadastro.js

document.addEventListener("DOMContentLoaded", function () {
    // 1. Data de Nascimento
    const dataInput = document.querySelector('[name="data_nascimento"]');
    if (dataInput) {
        Inputmask("99/99/9999").mask(dataInput);
    }

    // 2. CPF
    const cpfInput = document.querySelector('[name="cpf"]');
    if (cpfInput) {
        Inputmask("999.999.999-99").mask(cpfInput);
    }

    // 3. RG
    const rgInput = document.querySelector('[name="rg"]');
    if (rgInput) {
        Inputmask("99.999.999-9").mask(rgInput);
    }

    // 5. CEP
    const cepInput = document.querySelector('[name="endereco_cep"]');
    if (cepInput) {
        Inputmask("99999-999").mask(cepInput);
    }

    // 6. Telefone (Corrigido: Máscara Múltipla Manual e Robusta)
    const telefoneInput = document.querySelector('[name="telefone"]');
    if (telefoneInput) {
        Inputmask({
             mask: ["(99) 9999-9999", "(99) 99999-9999"], 
             keepStatic: true,
             greedy: false
        }).mask(telefoneInput);
    }
});