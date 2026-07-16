import { LitElement, html, css } from 'lit'

class MyApp extends LitElement {
  static styles = css`
    h1 { color: #4a90d9; }
  `

  render() {
    return html`
      <h1>{{ project_name }}</h1>
      <p>{{ description }}</p>
    `
  }
}

customElements.define('my-app', MyApp)
