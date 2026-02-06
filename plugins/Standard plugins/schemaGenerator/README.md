# JSON Schema Generator Plugin

## English

### Description
The **JSON Schema Generator** plugin allows you to automatically generate JSON schemas from your JSON data directly within the JWT & JSON Visual Editor. This tool is particularly useful for API documentation, validation, and understanding data structures.

### Features

#### Core Capabilities
- **Generate from Current File**: Automatically generates a JSON schema from the JSON content currently open in the editor
- **Multi-Example Support**: Load multiple JSON files as examples to generate a comprehensive schema that validates all of them
- **Observed Values**: The schema includes the actual values observed in your JSON as `enum` constraints
- **Save Schema**: Export the generated schema to a `.json` file
- **Copy to Clipboard**: Quickly copy the schema to your clipboard for use elsewhere
- **Clear Function**: Clear the generated schema display with one click
- **Multilingual Support**: Available in English, French, Spanish, Italian, and German

#### Advanced Features (NEW!)

##### Pattern Detection
The plugin now automatically detects common string patterns and adds appropriate JSON Schema `format` fields:
- **Email addresses** → `"format": "email"`
- **URLs** → `"format": "uri"`
- **ISO Dates** → `"format": "date"`
- **ISO Date-Times** → `"format": "date-time"`
- **UUIDs** → `"format": "uuid"`

**Example:**
```json
{
  "email": "user@example.com",
  "website": "https://example.com",
  "id": "550e8400-e29b-41d4-a716-446655440000"
}
```

Generated schema will include:
```json
{
  "properties": {
    "email": { "type": "string", "format": "email" },
    "website": { "type": "string", "format": "uri" },
    "id": { "type": "string", "format": "uuid" }
  }
}
```

##### Intelligent Array Analysis
Previously, only the **first element** of arrays was analyzed. Now:
- **All elements** are analyzed
- Schemas are merged to handle variations
- Mixed types are supported with `"type": ["string", "number"]`
- All unique enum values are collected

**Example:**
```json
{
  "items": [
    {"id": 1, "name": "Item A"},
    {"id": 2, "name": "Item B", "optional": true}
  ]
}
```

The generated schema will include **both** `name` and `optional` properties, with `optional` not marked as required (since it doesn't appear in all items).

##### Multi-Example Schema Generation
Generate a comprehensive schema from multiple JSON files:

1. Open your primary JSON file in the editor
2. Click "Add Example" to load additional JSON files
3. Generate the schema - it will validate **all** loaded examples
4. Fields present in all examples → marked as `required`
5. Fields present in some examples → optional
6. All observed enum values → merged

**Use Case:** When you have multiple API responses or data samples and want a schema that validates all variations.

### How to Use
1. Open a JSON file in the JWT & JSON Visual Editor
2. Navigate to **Tools** → **JSON Schema Generator**
3. Click **"Generate from Current File"** to create the schema
4. The schema will be displayed in the window
5. You can then:
   - **Save** it to a file
   - **Copy** it to your clipboard
   - Review and modify as needed

### Schema Generation Rules
- **Objects**: All keys become `required` properties
- **Arrays**: Schemas are inferred from **all elements** (merged)
- **Simple Values**: Included as `enum` with the observed value
- **Types**: Automatically detected (string, number, integer, boolean, null, object, array)
- **Patterns**: Emails, URLs, dates, UUIDs are detected with appropriate `format`

---

## Français

### Description
Le plugin **Générateur de schéma JSON** vous permet de générer automatiquement des schémas JSON à partir de vos données JSON directement dans l'éditeur JWT & JSON Visual Editor. Cet outil est particulièrement utile pour la documentation d'API, la validation et la compréhension des structures de données.

### Fonctionnalités

#### Capacités principales
- **Générer depuis le fichier actuel** : Génère automatiquement un schéma JSON à partir du contenu JSON actuellement ouvert dans l'éditeur
- **Support multi-exemples** : Chargez plusieurs fichiers JSON comme exemples pour générer un schéma complet qui valide tous
- **Valeurs observées** : Le schéma inclut les valeurs réelles observées dans votre JSON en tant que contraintes `enum`
- **Enregistrer le schéma** : Exportez le schéma généré vers un fichier `.json`
- **Copier dans le presse-papiers** : Copiez rapidement le schéma dans votre presse-papiers pour l'utiliser ailleurs
- **Fonction Effacer** : Effacez l'affichage du schéma généré en un clic
- **Support multilingue** : Disponible en anglais, français, espagnol, italien et allemand

#### Fonctionnalités avancées (NOUVEAU !)

##### Détection de Patterns
Le plugin détecte maintenant automatiquement les patterns de chaînes courants et ajoute les champs `format` appropriés au JSON Schema :
- **Adresses email** → `"format": "email"`
- **URLs** → `"format": "uri"`
- **Dates ISO** → `"format": "date"`
- **Date-Heures ISO** → `"format": "date-time"`
- **UUIDs** → `"format": "uuid"`

**Exemple :**
```json
{
  "email": "user@example.com",
  "website": "https://example.com",
  "id": "550e8400-e29b-41d4-a716-446655440000"
}
```

Le schéma généré inclura :
```json
{
  "properties": {
    "email": { "type": "string", "format": "email" },
    "website": { "type": "string", "format": "uri" },
    "id": { "type": "string", "format": "uuid" }
  }
}
```

##### Analyse Intelligente des Tableaux
Précédemment, seul le **premier élément** des tableaux était analysé. Maintenant :
- **Tous les éléments** sont analysés
- Les schémas sont fusionnés pour gérer les variations
- Les types mixtes sont supportés avec `"type": ["string", "number"]`
- Toutes les valeurs enum uniques sont collectées

**Exemple :**
```json
{
  "items": [
    {"id": 1, "name": "Item A"},
    {"id": 2, "name": "Item B", "optional": true}
  ]
}
```

Le schéma généré inclura **à la fois** les propriétés `name` et `optional`, avec `optional` non marqué comme requis (puisqu'il n'apparaît pas dans tous les éléments).

##### Génération de Schéma Multi-Exemples
Générez un schéma complet à partir de plusieurs fichiers JSON :

1. Ouvrez votre fichier JSON principal dans l'éditeur
2. Cliquez sur "Ajouter exemple" pour charger des fichiers JSON additionnels
3. Générez le schéma - il validera **tous** les exemples chargés
4. Champs présents dans tous les exemples → marqués comme `required`
5. Champs présents dans certains exemples → optionnels
6. Toutes les valeurs enum observées → fusionnées

**Cas d'usage :** Quand vous avez plusieurs réponses d'API ou échantillons de données et voulez un schéma qui valide toutes les variations.

### Utilisation
1. Ouvrez un fichier JSON dans l'éditeur JWT & JSON Visual Editor
2. Accédez à **Outils** → **Générateur de schéma JSON**
3. Cliquez sur **"Générer depuis le fichier actuel"** pour créer le schéma
4. Le schéma sera affiché dans la fenêtre
5. Vous pouvez ensuite :
   - **L'enregistrer** dans un fichier
   - **Le copier** dans votre presse-papiers
   - Le réviser et le modifier selon vos besoins

### Règles de génération du schéma
- **Objets** : Toutes les clés deviennent des propriétés `required`
- **Tableaux** : **Tous les éléments** sont analysés et les schémas fusionnés
- **Valeurs simples** : Incluses comme `enum` avec la valeur observée
- **Types** : Détectés automatiquement (string, number, integer, boolean, null, object, array)
- **Patterns** : Emails, URLs, dates, UUIDs sont détectés avec `format` approprié
