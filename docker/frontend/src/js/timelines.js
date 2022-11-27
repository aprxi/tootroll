
export const getHomeTimeline = async (hostUrl, accessToken) => {
    const url = `${hostUrl}/api/v1/timelines/home`

    const response = await fetch(
        url,
        {
            method: 'GET',
            headers: {
                'access_token': `${accessToken}`,
            }
        }
    )
    const json = await response.json();
    return json
}
