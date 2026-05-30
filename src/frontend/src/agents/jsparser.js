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
    const ast = parser.parse(code, {
        sourceType: "module",
        plugins: ["typescript", "jsx", "decorators-legacy"]
    });

    const codebaseMap = { classes: [], functions: [] };

    traverse(ast, {
        FunctionDeclaration(path) {
            if (path.node.id && path.node.start !== null && path.node.end !== null) {
                const bodyCode = code.slice(path.node.start, path.node.end);
                codebaseMap.functions.push({
                    name: path.node.id.name,
                    docstring: "", // Babel extraction for JSDoc can be added here if needed
                    doc_hash: "",
                    body: bodyCode,
                    body_hash: calculateHash(bodyCode)
                });
            }
        },
        ClassDeclaration(path) {
            if (path.node.id && path.node.start !== null && path.node.end !== null) {
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
        ClassMethod(path) {
            if (path.node.key && path.node.key.type === 'Identifier' && path.node.start !== null && path.node.end !== null) {
                const bodyCode = code.slice(path.node.start, path.node.end);
                codebaseMap.functions.push({
                    name: path.node.key.name,
                    docstring: "",
                    doc_hash: "",
                    body: bodyCode,
                    body_hash: calculateHash(bodyCode)
                });
            }
        }
    });

    console.log(JSON.stringify(codebaseMap));
} catch (error) {
    console.error(JSON.stringify({ error: error.message }));
    process.exit(1);
}
