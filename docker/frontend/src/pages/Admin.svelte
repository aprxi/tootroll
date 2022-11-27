<script>
    let apiUrl = "http://localhost:8888"

    const writeConfig = () => {
        console.log("Writing config...")
    }
</script>

<p>Enter apiUrl:</p>
<input bind:value={apiUrl}>

<button on:click={writeConfig}>
	Save
</button>
