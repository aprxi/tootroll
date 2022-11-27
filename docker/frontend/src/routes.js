// Components
import Home from './pages/Home.svelte'
import Public from './pages/Public.svelte'
import Admin from './pages/Admin.svelte'
import NotFound from './pages/NotFound.svelte'


// Export the route definition object
export default {
    // Exact path
    '/': Home,
    // Using named parameters, with last being optional
    // '/hello/:first/:last?': Name,
    // Wildcard parameter
    // Included twice to match both `/wild` (and nothing after) and `/wild/*` (with anything after)
    // '/wild/*': Wild,
    '/Home': Home,
    '/Public': Public,
    '/Admin': Admin,
    // Catch-all, must be last
    '*': NotFound,
}
