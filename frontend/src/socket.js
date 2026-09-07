import { io } from "socket.io-client"
import { socketio_port } from "../../../../sites/common_site_config.json"
export function initSocket() {
  let siteName = window.site_name || "drive.localhost"

  let default_port = window.socketio_port || socketio_port || "9000"
  let port = window.location.port ? `:${default_port}` : ""
  // No explicit port means default 80/443: follow the page protocol
  // instead of forcing https, so plain-http sites work too. (BOR)
  let protocol = port ? "http" : window.location.protocol.replace(":", "")
  let host = window.location.hostname

  let url = `${protocol}://${host}${port}/${siteName}`
  let socket = io(url, {
    withCredentials: true,
    reconnectionAttempts: 5,
  })
  socket.on("connect_error", (data) => {
    console.log(data)
  })
  return socket
}
