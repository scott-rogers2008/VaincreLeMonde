const fs = require('fs');
const crypto = require('crypto');
const parser = require('@babel/parser');
const traverse = require('@babel/traverse').default;

// Node index 2 is your file path
const filePath = process.argv[2];

if (!filePath) {
    console.error(JSON.stringify({ error: "Missing file path argument" }));
    process.exit(1);
}

function calculateHash(text) {
    return crypto.createHash('sha256').update(text, 'utf8').digest('hex');
}

try {
    const code = fs.readFileSync(filePath, 'utf-8');
    const codebaseMap = { classes: [], functions: [] };

    // Direct extraction fallback routing for markup and style files
    if (filePath.endsWith('.html')) {
        codebaseMap.functions.push({
            name: "HTML_Template_Body",
            docstring: "Raw HTML Presentation view component markup text",
            doc_hash: "",
            body: code,
            body_hash: calculateHash(code)
        });
        console.log(JSON.stringify(codebaseMap));
        process.exit(0);
    } 
    
    if (filePath.endsWith('.css')) {
        codebaseMap.functions.push({
            name: "CSS_Style_Rules",
            docstring: "Raw CSS layout definitions sheet style rules",
            doc_hash: "",
            body: code,
            body_hash: calculateHash(code)
        });
        console.log(JSON.stringify(codebaseMap));
        process.exit(0);
    }

    // Standard Babel traversal fallback engine for JavaScript / TypeScript source paths
    const ast = parser.parse(code, {
        sourceType: "module",
        plugins: ["typescript", "jsx", "decorators-legacy"]
    });

    traverse(ast, {
        // Pattern 1: Standard Named Functions
        FunctionDeclaration(path) {
            if (path.node.id && typeof path.node.start === 'number' && typeof path.node.end === 'number') {
                const bodyCode = code.slice(path.node.start, path.node.end);
                codebaseMap.functions.push({
                    name: path.node.id.name,
                    docstring: "", 
                    doc_hash: "",
                    body: bodyCode,
                    body_hash: calculateHash(bodyCode)
                });
            }
        },

        // Pattern 2: Class Blueprint Frameworks
        ClassDeclaration(path) {
            if (path.node.id && typeof path.node.start === 'number' && typeof path.node.end === 'number') {
                const bodyCode = code.slice(path.node.start, path.node.end);
                codebaseMap.classes.push({
                    name: path.node.id.name,
                    docstring: "",
                    doc_hash: "",
                    body: bodyCode,
                    body_hash: calculateHash(bodyCode)
                });
            }
        },

        // Pattern 3: Standard Methods Inside Classes
        ClassMethod(path) {
            if (path.node.key && path.node.key.type === 'Identifier' && typeof path.node.start === 'number' && typeof path.node.end === 'number') {
                const bodyCode = code.slice(path.node.start, path.node.end);
                codebaseMap.functions.push({
                    name: path.node.key.name,
                    docstring: "",
                    doc_hash: "",
                    body: bodyCode,
                    body_hash: calculateHash(bodyCode)
                });
            }
        },

        // Pattern 4: Modern TypeScript Arrow Functions (Variable Declarations)
        VariableDeclarator(path) {
            if (path.node.id && path.node.id.type === 'Identifier' && path.node.init && 
               (path.node.init.type === 'ArrowFunctionExpression' || path.node.init.type === 'FunctionExpression')) {
                
                if (typeof path.node.start === 'number' && typeof path.node.end === 'number') {
                    const bodyCode = code.slice(path.node.start, path.node.end);
                    codebaseMap.functions.push({
                        name: path.node.id.name,
                        docstring: "",
                        doc_hash: "",
                        body: bodyCode,
                        body_hash: calculateHash(bodyCode)
                    });
                }
            }
        }
    });

    console.log(JSON.stringify(codebaseMap));
} catch (error) {
    console.error(JSON.stringify({ error: error.message }));
    process.exit(1);
}
