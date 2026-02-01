/**
 * Simple accessibility tests for the frontend app.
 * These tests check for common accessibility patterns.
 *
 * Run with: node tests/test_accessibility.js
 */

const fs = require('fs');
const path = require('path');

// Read the HTML file
const htmlPath = path.join(__dirname, '..', 'src', 'index.html');
const html = fs.readFileSync(htmlPath, 'utf-8');

// Read the CSS file
const cssPath = path.join(__dirname, '..', 'src', 'styles.css');
const css = fs.readFileSync(cssPath, 'utf-8');

// Read the JS file
const jsPath = path.join(__dirname, '..', 'src', 'app.js');
const js = fs.readFileSync(jsPath, 'utf-8');

let passed = 0;
let failed = 0;

function test(name, condition) {
    if (condition) {
        console.log(`✓ ${name}`);
        passed++;
    } else {
        console.log(`✗ ${name}`);
        failed++;
    }
}

console.log('Running accessibility tests...\n');

// HTML Structure Tests
console.log('--- HTML Structure ---');
test('Has lang attribute on html element', html.includes('lang='));
test('Uses semantic header element', html.includes('<header'));
test('Uses semantic main element', html.includes('<main'));
test('Uses semantic footer element', html.includes('<footer'));
test('Uses semantic nav element', html.includes('<nav'));
test('Has skip link for keyboard users', html.includes('skip') && html.includes('#main'));

// Form Accessibility Tests
console.log('\n--- Form Accessibility ---');
test('Input has associated label', html.includes('<label') && html.includes('for='));
test('Button has accessible name', !html.includes('>+</button>') || html.includes('aria-label'));

// Image Accessibility Tests
console.log('\n--- Image Accessibility ---');
test('Images have alt attributes', !html.includes('<img') || html.includes('alt='));

// Interactive Elements Tests
console.log('\n--- Interactive Elements ---');
test('Clickable items use button or link elements', !html.includes('onclick="toggleTask') || html.includes('<button'));
test('Delete buttons have accessible labels', html.includes('aria-label="Delete') || html.includes('aria-label="Remove'));

// CSS Accessibility Tests
console.log('\n--- CSS Accessibility ---');
test('Has focus styles defined', css.includes(':focus'));
test('Uses relative units (rem/em)', css.includes('rem') || css.includes('em'));
test('Has responsive breakpoints', css.includes('@media'));
test('Respects reduced motion preference', css.includes('prefers-reduced-motion'));

// JavaScript Accessibility Tests
console.log('\n--- JavaScript Accessibility ---');
test('Handles keyboard events', js.includes('keydown') || js.includes('keypress') || js.includes('keyup'));
test('Uses ARIA live regions', js.includes('aria-live') || js.includes('role="status"') || js.includes('role="alert"'));
test('Manages focus after actions', js.includes('.focus()'));

// Summary
console.log('\n--- Summary ---');
console.log(`Passed: ${passed}`);
console.log(`Failed: ${failed}`);
console.log(`Total: ${passed + failed}`);

// Exit with error code if tests failed
process.exit(failed > 0 ? 1 : 0);
