<<<<<<< HEAD
# <div align="center"> <img width="300" height="300" alt="ilustracao" src="https://github.com/user-attachments/assets/7099b97f-5573-4089-85ab-f96e19184762" /> <br>[![Python 3.13.2](https://img.shields.io/badge/Python-3.13.2-3776AB?logo=python&logoColor=white)](https://www.python.org/downloads/release/python-3132/) [![Django 5.2.2](https://img.shields.io/badge/Django-5.2.2-092E20?logo=django&logoColor=white)](https://docs.djangoproject.com/en/5.2/) [![Bootstrap 5.3.6](https://img.shields.io/badge/Bootstrap-5.3.6-7952B3?logo=bootstrap&logoColor=white)](https://getbootstrap.com/docs/5.3/)</div>

Olá! Este é um projeto de um Sistema de Gerenciamento de Escola por nome CORE que foi desenvolvido pelos alunos do IF Baiano - Campus Guanambi.<br>
São eles: <div align="center">
  | Adriel Lima                                                                                                                                                                                            | Emilly Victoria                                                                                                                                                                                         | Vinícius Morais                                                                                                                                                                                           |
  | :-----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------: | :-----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------: | :-----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------: |
  | <a href="https://www.instagram.com/wrttdriel/"><img src="https://github.com/user-attachments/assets/45e6c560-ff1b-4bd7-9ea0-2ec6b8cfc48a" width="150" height="150"/></a> | <a href="https://www.instagram.com/emillyszf/"><img src="https://github.com/user-attachments/assets/c2c12f03-74d8-430a-9314-cc23353de29b" width="150" height="150"/></a> | <a href="https://www.instagram.com/wtfvinaa/"><img src="https://github.com/user-attachments/assets/ed14cfb8-6721-43e9-a474-da1c94e16ee5" width="150" height="150"/></a> |
</div>

---

## Instruções para Rodar o Projeto

Para configurar e rodar o projeto, siga os passos abaixo.

### Pré-requisitos

Certifique-se de ter os seguintes softwares instalados antes de iniciar:

* **Python 3.13.2**: [Baixe aqui](https://www.python.org/downloads/release/python-3132/)
* **VS Code**: [Baixe aqui](https://code.visualstudio.com/download)

### Configuração do Ambiente

1.  **Baixe e Abra o Projeto:**
    * Clone ou baixe o repositório do GitHub para o seu computador.
    * Caso **BAIXE**, recomendamos renomear a pasta para `core`.
    * Para abrir o projeto no VS Code, selecione a pasta `core` e clique com o botão direito. Vá em "Mostrar mais opções" e depois em "Abrir com Code".<br>
        ![Image of folder selection in VS Code](https://github.com/user-attachments/assets/457d52cf-5156-4217-9aeb-3edb364f660e)<br>
        ![Image of "Open with Code" option](https://github.com/user-attachments/assets/8e63ea94-f864-45c8-885c-7fa7b22a1eb3)<br>

    * Ao abrir, confirme a confiança nos autores da pasta, se solicitado:<br>
        ![Image of trust prompt in VS Code](https://github.com/user-attachments/assets/201a63d6-f321-4629-911b-4b32a995d162)<br><br>
    * Caso **CLONE**, crie uma pasta para o nome `core` para depois fazer os processos ensinados anteriormente de "Abrir com Code".<br>
    *  No terminal, que tem a seguir um tutorial de como abrir, com ele aberto cole o seguinte código antes de fazer qualquer coisa:
         ```bash
         git clone https://github.com/driizin/core.git
         ```
         ![image](https://github.com/user-attachments/assets/df43ebad-15b8-44c2-8c4b-6873b0b7ae80)


2.  **Abra o Terminal no VS Code:**
   * No VS Code, abra o arquivo `manage.py` no lado esquerdo.<br>
        ![Image of main.py in VS Code sidebar](https://github.com/user-attachments/assets/6a95ecc8-797f-4740-bbe4-4de8b5393209)<br>
   * Vá na parte superior do aplicativo e selecione **Terminal > Novo Terminal**.<br>
        ![Image of Terminal menu in VS Code](https://github.com/user-attachments/assets/56dd7070-7d93-473a-a69a-f211f3ad9b64)<br>
        ![Image of New Terminal option](https://github.com/user-attachments/assets/953ca9ed-fcd8-4601-8234-585e12bd2437)<br>
        ![Image of terminal type selection in VS Code](https://github.com/user-attachments/assets/121e2d2b-e025-4b3a-bdb1-2db1f2a9d592)<br>


4.  **Crie e Ative o Ambiente Virtual:**
    * Para criar um ambiente virtual chamado `psw` (recomendado para isolar as dependências do projeto), execute:
        ```bash
        py -3.13 -m venv psw
        ```
        ![Image of venv creation command](https://github.com/user-attachments/assets/2cfb0f82-43c3-442c-b559-29f30de68add)

    * Ative o ambiente virtual. Você deve ver `(psw)` no início da linha de comando. **Os comandos de ativação variam de acordo com o sistema operacional:**
        * **No Windows (CMD/PowerShell):**
            ```bash
            .\psw\Scripts\activate
            ```
            ![Image of Windows virtual environment activation](https://github.com/user-attachments/assets/07aed937-7561-4836-a72c-1c0a55e81c65)

        * **No Linux / macOS (Bash/Zsh):**
            ```bash
            source psw/Scripts/activate
            ```
            ![Image of Linux and macOS virtual environment activation](https://github.com/user-attachments/assets/75912e3e-9dcf-424a-9cdc-0680c0309168)

    * Verifique se o VS Code está usando o interpretador Python correto (Python 3.13 do ambiente `psw`). Ele aparece no canto inferior direito. Se não estiver, clique nele e selecione "Python 3.13.2 ('psw':venv)".<br>
        ![Image of Python interpreter selection in VS Code](https://github.com/user-attachments/assets/3607090a-789d-4ade-88cf-b8edfd5de12e)<br>
        ![Image of Python versions list](https://github.com/user-attachments/assets/00734203-4a80-4967-bd9a-770aaa99044c)

5.  **Instale as Dependências do Projeto:**
    Com o ambiente virtual **`psw`** ativado, instale todas as bibliotecas Python necessárias para o projeto. O arquivo `requirements.txt` garante que todas as dependências sejam instaladas nas versões exatas, assegurando a compatibilidade e a funcionalidade do Projeto.

    No terminal, execute:
    ```bash
    pip install -r requirements.txt
    ```
    ![Image of Installing dependences](https://github.com/user-attachments/assets/893f1b6f-85d6-4433-be35-7db9c67a33e8)<br>
    
### Rodando o Projeto

1.  **Inicie o Servidor do Projeto:**
    * Com todas as configurações anteriores feitas e seu ambiente virtual `psw` ativado no terminal do VS Code:
    * No terminal digite isso:<br>
    ```bash
    python manage.py runserver
    ```

2.  **Acesse o Projeto no Navegador:**
    * Após iniciar o servidor, o terminal indicará o endereço local onde o Projeto está rodando. Geralmente, será:
        http://127.0.0.1:8000
        ![Image of Projeto running on localhost](https://github.com/user-attachments/assets/d3b9a4bc-d3c2-448d-b8bb-035c1d0a40a0)<br>

    * Abra seu navegador e acesse esse endereço.

    **Apresentação Vídeo do Projeto:**
    
    <iframe width="560" height="315" src="https://www.youtube.com/embed/eVnCa5wuwdU?si=7kCFDV-bTc-Wo-D9" title="YouTube video player" frameborder="0" allow="accelerometer; autoplay; clipboard-write; encrypted-media; gyroscope; picture-in-picture; web-share" referrerpolicy="strict-origin-when-cross-origin" allowfullscreen></iframe>
=======
# CEEP
>>>>>>> dc5164ad2b3aede42d0758f85aa4964f35e64140
