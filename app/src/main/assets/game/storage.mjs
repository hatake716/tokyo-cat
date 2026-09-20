let connection;
export function database() {
  if (connection) return connection;
  connection = new Promise((resolve, reject) => {
    const req = indexedDB.open("tokyo-cat-album", 1);
    req.onupgradeneeded = () =>
      req.result.createObjectStore("photos", { keyPath: "id" });
    req.onsuccess = () => resolve(req.result);
    req.onerror = () => {
      connection = null;
      reject(req.error);
    };
  });
  return connection;
}
export async function addPhoto(photo) {
  const db = await database();
  return new Promise((resolve, reject) => {
    const tx = db.transaction("photos", "readwrite");
    tx.objectStore("photos").add(photo);
    tx.oncomplete = () => resolve(photo);
    tx.onerror = () => reject(tx.error);
    tx.onabort = () => reject(tx.error);
  });
}
export async function photos() {
  const db = await database();
  return new Promise((resolve, reject) => {
    const req = db.transaction("photos").objectStore("photos").getAll();
    req.onsuccess = () => resolve(req.result.sort((a, b) => b.time - a.time));
    req.onerror = () => reject(req.error);
  });
}
export async function removePhoto(id) {
  const db = await database();
  return new Promise((resolve, reject) => {
    const tx = db.transaction("photos", "readwrite");
    tx.objectStore("photos").delete(id);
    tx.oncomplete = resolve;
    tx.onerror = () => reject(tx.error);
  });
}
