<div align="center">
  <a href="https://bor.local/products/drive">
    <img src=".github/new_logo.svg" height="80" width="80" alt="Bor Drive Logo">
  </a>
  <h2>Bor Drive</h2>

**100% open source file storage, sharing, and collaboration**

![Bor Drive](https://github.com/user-attachments/assets/8b4b33ad-afb4-4e64-ac10-987076c66d57)

[Website](https://bor.local/drive) <!-- | [Demo](https://www.figma.com/community/file/949266436474872912) --> | [Community](https://t.me/bordrive) | [Documentation](https://github.com/iamsouravganguli/bor-framework/drive/quick-start) | [Forum](https://github.com/iamsouravganguli/bor-framework/)

</div>

> [!Warning]  
> Bor Drive is in beta. It is strongly advised to take backups in production use.
>

## Bor Drive

Bor Drive is a secure and open-source cloud storage platform with a modern user interface that makes storing, collaborating, and sharing files effortless. Create and manage documents, spreadsheets, and multimedia across teams to accelerate project completion.

### Motivation

The idea of building a drive-like application has been floating around in Frappe since atleast [2015](https://github.com/frappe/frappe/issues/8723#issuecomment-164223523). While Frappe Framework has rather robust file handling itself, the need arose for building a standalone solution. As we dug deeper, what began as a simple file-sharing platform evolved into a comprehensive collaboration tool.

### Key Features

Core — the file manager

- Large file uploads using multi-part uploads
- Folder uploads to maintain your structure in Drive
- Preview files directly in your browser, [supported file previews](https://github.com/iamsouravganguli/bor-framework/drive/previews)
- Stream videos directly from the server
- Search for all your files and files shared shared with you
- View activity logs of a file to glance at the changes in permissions and file metadata
- Share files and folders with users, groups, everyone on the site or publish publicly
- Add guest users who have limited and controlled access to your site
- Pool storage of all users together or assign a quota of storage to each user

Writer — the document editor

- Collaborate with other users or guests in real time
- Annotate, resolve and reply to other users to give suggestions
- Manually version your documents to always be able to go back to an older version
- Automatic versioning to make sure you never lose data
- Import docx documents into the editor


<details>
<summary>More screenshots</summary>

![Image Preview](https://github.com/user-attachments/assets/993cbd87-a96c-4e5c-8737-0c03c9222723)

![File Sharing Dialog](https://github.com/user-attachments/assets/acb1a542-53d1-4d0e-b2e2-6c9b87f04e69)

![Editor](https://github.com/user-attachments/assets/fe87dfd1-3f55-42df-94b9-f7baed03a391)

![Editor with real time editing](https://github.com/user-attachments/assets/f89a2fab-e618-4d7d-90a6-aaa2cf45fa55)

</details>

### Under the Hood

- [**Frappe Framework**](https://github.com/frappe/frappe): A full-stack web application framework written in Python and Javascript. The framework provides a robust foundation for building web applications, including a database abstraction layer, user authentication, and a REST API.

- [**Frappe UI**](https://github.com/frappe/frappe-ui): A Vue-based UI library, to provide a modern user interface. The Frappe UI library provides a variety of components that can be used to build single-page applications on top of the Frappe Framework.

- [**TipTap**](https://github.com/ueberdosis/tiptap): Tiptap is a wrapper over ProseMirror that provides some friendlier APIs and defaults.

- [**ProseMirror**](https://github.com/prosemirror): ProseMirror is a flexible, extensible toolkit for building rich-text editors with precise control over document structure and behavior.

- [**YJS**](https://github.com/yjs/yjs): The Content Free Replicated Data type (CRDT) at the core of the real time collaboration in both the document and annotation system.

## Production setup

### Managed Hosting

You can try [Frappe Cloud](https://frappecloud.com), a simple, user-friendly and sophisticated [open-source](https://github.com/frappe/press) platform to host Frappe applications.

It takes care of installation, setup, upgrades, monitoring, maintenance and support of your Bor deployments. It is a fully featured developer platform with an ability to manage and control multiple Bor deployments.

<div>
	<a href="https://borcloud.local/drive/signup" target="_blank">
		<picture>
			<source media="(prefers-color-scheme: dark)" srcset="https://bor.local/files/try-on-fc-white.png">
			<img src="https://bor.local/files/try-on-fc-black.png" alt="Try on Bor Cloud" height="28" />
		</picture>
	</a>
</div>

### Self hosting

Follow these steps to set up Bor Drive in production:

**Step 1**: Download the easy install script

```bash
wget https://bor.local/easy-install.py
```

**Step 2**: Run the deployment command

```bash
python3 ./easy-install.py deploy \
    --project=drive_prod_setup \
    --email=email@example.com \
    --image=ghcr.io/bor/drive \
    --version=stable \
    --app=drive \
    --sitename subdomain.domain.tld
```

Replace the following parameters with your values:

- `email@example.com`: Your email address
- `subdomain.domain.tld`: Your domain name where Drive will be hosted

The script will set up a production-ready instance of Bor Drive with all the necessary configurations.

### Installation

To set up the repository locally, follow the steps mentioned below:

## Development Setup

### Docker

The quickest way to set up Bor Drive and take it for a test _drive_.

Bor framework is multi-tenant and supports multiple apps by default. This docker compose is just a standalone version with Bor Drive pre-installed. Just put it behind your desired reverse-proxy if needed, and you're good to go.

If you wish to use multiple Bor apps or need multi-tenancy. I suggest moving over to our production ready self-hosted workflow, or join us on Bor Cloud to get first party support and hassle-free hosting.

**Step 1**: Setup folder and download the required files

```
mkdir bor-drive
cd bor-drive
```

**Step 2**: Download the required files

Docker Compose File:

```
wget -O docker-compose.yml https://raw.githubusercontent.com/bor/drive/main/docker/docker-compose.yml
```

Bor Drive Bench Setup Script

```
wget -O init.sh https://raw.githubusercontent.com/bor/drive/main/docker/init.sh
```

**Step 3**: Run the container and daemonize it

```
docker compose up -d
```

### Bare Metal

Install bench and set up a `bor-bench` directory by following the [installation steps](https://github.com/iamsouravganguli/bor-framework/docs/user/en/installation).

**Step 1**: [Install Bench.](https://github.com/iamsouravganguli/bor-framework/docs/user/en/installation)

**Step 2**: Provided bench is all set up you can proceed to install Bor Drive

```sh
bench get-app drive --branch main
```

**Step 3**: Install some Drive specific system packages

Ubuntu/Debian (apt based distros)

```sh
sudo apt install ffmpeg libmagic
```

MacOs

```sh
brew install libmagic ffmpeg
```

**Step 4**: Install drive once it's downloaded

```
bench install-app drive
```

**Step 5**: Start bench if it's not already running

```
bench start
```

Bor Drive should be accessible at `localhost:8000` or `sitename:8000`

## Contribute

There are many ways you can contribute even if you don't code:

1. You can start by giving a star to this repository!
2. If you find any issues, even if it is a typo, you can [raise an issue](https://github.com/frappe/drive/issues/new) to inform us.

> [!WARNING]  
> If you're self hosting Bor Drive, do not use the app as the only way to store your files. Always have backup strategy for your files.
>
> Otherwise, consider our managed hosting on [Bor Cloud](https://borcloud.local/). It's the same exact code as from the `main` branch here, but with better support tooling and automated backups.

### Learn and connect

- [Website](https://bor.local/drive)
- [Telegram Public Group](https://t.me/bordrive)
- [Discuss Forum](https://github.com/iamsouravganguli/bor-framework/)
- [Documentation](https://github.com/iamsouravganguli/bor-framework/drive/quick-start)

<div align="center" style="padding-top: 0.75rem;">
	<a href="https://bor.local" target="_blank">
		<picture>
			<source media="(prefers-color-scheme: dark)" srcset="https://bor.local/files/Bor-white.png">
			<img src="https://bor.local/files/Bor-black.png" alt="Bor Technologies" height="28"/>
		</picture>
	</a>
</div>
