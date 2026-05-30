const fs = require('fs');
const parser = require('@babel/parser');
const traverse = require('@babel/traverse').default;

// Node index 0 is 'node', index 1 is 'jsparser.js', index 2 is your file path
const filePath = process.argv[2]; 

if (!filePath) {
    console.error(JSON.stringify({ error: "Missing file path argument" }));
    process.exit(1);
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
            if (path.node.id) {
                codebaseMap.functions.push({ name: path.node.id.name, docstring: "", doc_hash: "", body: "", body_hash: "" });
            }
        },
        ClassDeclaration(path) {
            if (path.node.id) {
                codebaseMap.classes.push({ name: path.node.id.name, docstring: "", doc_hash: "", body: "", body_hash: "" });
            }
        },
        ClassMethod(path) {
            if (path.node.key && path.node.key.type === 'Identifier') {
                codebaseMap.functions.push({ name: path.node.key.name, docstring: "", doc_hash: "", body: "", body_hash: "" });
            }
        }
    });

    console.log(JSON.stringify(codebaseMap));
} catch (error) {
    console.error(JSON.stringify({ error: error.message }));
    process.exit(1);
}
