<script>
    import { onMount } from 'svelte'
    import { getHomeTimeline } from '../js/timelines'

    const hostUrl = "http://localhost:8888"
    const accessToken = "dummy_token"
    let tootList = []

    onMount(async () => {
        tootList = await getHomeTimeline(hostUrl, accessToken)
    })

</script>

<div class="page-wrapper">
{#if !tootList}
    <p>No toots</p>
{:else}
    <b>Toots: {tootList.length}</b>
    {#each tootList as toot}

    {#if toot.reblog}
        <div class="toot">
            <div class="row reference">
                <p>Reblog by
                    <strong>{toot.account.username}</strong>
                </p>
            </div>
            <div class="row">
                <div class="column-1">
                    <div class="avatar">
                        <img src="{toot.reblog.account.avatar}" alt="Image">
                    </div>
                </div>
                <div class="column-9">
                    <div class="content">
                        <strong>{toot.reblog.account.username}</strong> <small>{toot.reblog.account.acct}</small> <small>{toot.reblog.created_at}</small>
                        {@html toot.reblog.content}
                    </div>
                </div>
            </div>
        </div>
    {:else}
        <div class="toot">
            <div class="row">
                <div class="column-1">
                    <div class="avatar">
                        <img src="{toot.account.avatar}" alt="Image">
                    </div>
                </div>
                <div class="column-9">
                    <div class="content">
                        <strong>{toot.account.username}</strong> <small>{toot.account.acct}</small> <small>{toot.created_at}</small>
                        {@html toot.content}
                    </div>
                </div>
            </div>
        </div>
    {/if}

    {:else}
        <p>No toots</p>
    {/each}
{/if}
</div> 